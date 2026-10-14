// VoyageML — Smart Journey Predictor Frontend Script
let leafletMap = null;
let currentRouteLayer = null;
let sourceMarker = null;
let destMarker = null;
let currentTravelMode = "DRIVE";
let lastJourneySource = "";
let lastJourneyDest = "";
let lastDepartureDate = "";
let lastDepartureTime = "";
let lastTrafficCondition = "Moderate";

const MODE_LABELS = {
    DRIVE: { name: "Car", emoji: "🚗", tag: "🚗 CAR" },
    TWO_WHEELER: { name: "Two-Wheeler", emoji: "🏍️", tag: "🏍️ TWO-WHEELER" },
    TRANSIT: { name: "Transit", emoji: "🚌", tag: "🚌 TRANSIT" },
    WALK: { name: "Walking", emoji: "🚶", tag: "🚶 WALK" }
};

let departureOption = "NOW"; // "NOW" or "PLANNED"
let isUsingCurrentLocation = false;
let currentLocationCoords = null; // { lat, lon }
let currentLocationName = "";
let selectedDestinationCoords = null; // { lat, lon, name, address }

document.addEventListener("DOMContentLoaded", () => {
    initApp();
});

function initApp() {
    // 1. Set default departure date input to today's date (YYYY-MM-DD)
    const dateInput = document.getElementById("departure_date");
    if (dateInput && !dateInput.value) {
        const todayStr = new Date().toISOString().split("T")[0];
        dateInput.value = todayStr;
    }

    // 2. Setup Selectors & Form Events
    setupTravelModeSelector();
    setupDepartureTypeSelector();
    setupTrafficConditionSelector();
    setupCurrentLocationHandler();
    setupDestinationSearchHandler();

    // 3. Attach Form Submit Event
    const form = document.getElementById("travel-form");
    if (form) {
        form.addEventListener("submit", handleFormSubmit);
    }

    // 4. Initialize Leaflet Map & Navigation Engine
    initLeafletMap();
    setupNavigationHandlers();
}

function setupCurrentLocationHandler() {
    const locBtn = document.getElementById("use-current-loc-btn");
    const sourceInput = document.getElementById("source");

    if (!locBtn || !sourceInput) return;

    locBtn.addEventListener("click", () => {
        if (!navigator.geolocation) {
            showLocationError("Unable to detect your location. Please enter your starting location manually.");
            return;
        }

        hideLocationError();
        const originalBtnHTML = locBtn.innerHTML;
        locBtn.disabled = true;
        locBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Detecting...`;

        navigator.geolocation.getCurrentPosition(
            async (position) => {
                const lat = position.coords.latitude;
                const lon = position.coords.longitude;
                currentLocationCoords = { lat, lon };
                isUsingCurrentLocation = true;

                locBtn.classList.add("active");
                locBtn.disabled = false;
                locBtn.innerHTML = originalBtnHTML;

                let displayLocationName = "Current Location";

                // Reverse geocoding via Nominatim
                try {
                    const revUrl = `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`;
                    const res = await fetch(revUrl, {
                        headers: { "Accept-Language": "en" }
                    });
                    if (res.ok) {
                        const data = await res.json();
                        if (data && data.address) {
                            const addr = data.address;
                            displayLocationName = addr.suburb || addr.neighbourhood || addr.city || addr.town || addr.village || addr.county || (data.display_name ? data.display_name.split(",")[0] : "Current Location");
                        } else if (data && data.display_name) {
                            displayLocationName = data.display_name.split(",")[0];
                        }
                    }
                } catch (e) {
                    console.warn("Nominatim reverse geocode notice:", e);
                    displayLocationName = "Current Location";
                }

                currentLocationName = displayLocationName;
                sourceInput.value = `📍 ${displayLocationName}`;
                hideLocationError();
            },
            (error) => {
                locBtn.disabled = false;
                locBtn.innerHTML = originalBtnHTML;
                locBtn.classList.remove("active");
                isUsingCurrentLocation = false;
                currentLocationCoords = null;

                if (error.code === error.PERMISSION_DENIED) {
                    showLocationError("Location permission was denied. Please enter your starting location manually.");
                } else {
                    showLocationError("Unable to detect your location. Please enter your starting location manually.");
                }
            },
            {
                enableHighAccuracy: true,
                timeout: 10000,
                maximumAge: 0
            }
        );
    });

    // Revert to manual entry if user types or changes the source field
    sourceInput.addEventListener("input", () => {
        isUsingCurrentLocation = false;
        currentLocationCoords = null;
        currentLocationName = "";
        if (locBtn) locBtn.classList.remove("active");
        hideLocationError();
    });
}

function showLocationError(msg) {
    const errorMsgBox = document.getElementById("location-error-msg");
    if (errorMsgBox) {
        errorMsgBox.innerHTML = `<i class="fa-solid fa-triangle-exclamation"></i> ${msg}`;
        errorMsgBox.style.display = "flex";
    }
}

function hideLocationError() {
    const errorMsgBox = document.getElementById("location-error-msg");
    if (errorMsgBox) {
        errorMsgBox.style.display = "none";
        errorMsgBox.innerHTML = "";
    }
}

/* ==================================================
 * DESTINATION PLACE SEARCH & SELECTION LOGIC
 * ================================================== */
function setupDestinationSearchHandler() {
    const destInput = document.getElementById("destination");
    const searchBtn = document.getElementById("dest-search-btn");
    const dropdown = document.getElementById("dest-results-dropdown");

    if (!destInput) return;

    if (searchBtn) {
        searchBtn.addEventListener("click", () => {
            triggerDestinationSearch();
        });
    }

    destInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();
            triggerDestinationSearch();
        }
    });

    destInput.addEventListener("input", () => {
        selectedDestinationCoords = null;
        hideSelectedPlaceInfo();
        if (dropdown) dropdown.style.display = "none";
    });
}

async function performPlaceSearch(query) {
    const cleanQuery = query.replace(/📍\s*/g, '').trim();
    if (!cleanQuery) return [];

    let results = [];

    // 1. Try backend Nominatim search endpoint
    try {
        const res = await fetch(`/api/search-place?q=${encodeURIComponent(cleanQuery)}`);
        if (res.ok) {
            const data = await res.json();
            if (data && data.success && Array.isArray(data.results)) {
                results = data.results;
            }
        }
    } catch (e) {
        console.warn("Backend place search notice:", e);
    }

    // 2. Direct Nominatim fallback if backend returned no results
    if (!results || results.length === 0) {
        try {
            const nomUrl = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(cleanQuery)}&format=json&addressdetails=1&limit=10`;
            const res = await fetch(nomUrl, { headers: { "Accept-Language": "en" } });
            if (res.ok) {
                const data = await res.json();
                if (Array.isArray(data) && data.length > 0) {
                    results = data.map(item => {
                        const lat = parseFloat(item.lat);
                        const lon = parseFloat(item.lon);
                        const addr = item.address || {};
                        const placeName = addr.amenity || addr.shop || addr.building || addr.tourism || addr.hospital || addr.school || addr.university || addr.mall || item.name || (item.display_name ? item.display_name.split(",")[0] : cleanQuery);

                        const addrParts = [];
                        for (const k of ["road", "suburb", "neighbourhood", "city_district", "city", "town", "village", "state"]) {
                            if (addr[k] && !addrParts.includes(addr[k]) && addr[k] !== placeName) {
                                addrParts.push(addr[k]);
                            }
                        }
                        const dispAddr = addrParts.length > 0 ? addrParts.join(", ") : (item.display_name || cleanQuery);

                        return {
                            place_name: placeName,
                            display_name: item.display_name || placeName,
                            display_address: dispAddr,
                            latitude: lat,
                            longitude: lon,
                            place_type: item.type || item.class || "location"
                        };
                    });
                }
            }
        } catch (err) {
            console.warn("Direct Nominatim search notice:", err);
        }
    }

    return results;
}

async function triggerDestinationSearch() {
    const destInput = document.getElementById("destination");
    const query = destInput ? destInput.value.trim() : "";

    if (!query) {
        showSearchError("Please enter a place name, shop, landmark, or address.");
        return;
    }

    showSearchLoading();

    const results = await performPlaceSearch(query);

    if (!results || results.length === 0) {
        showSearchError("Place not found. Try entering a more specific name or address.");
        return;
    }

    if (results.length === 1) {
        selectDestinationPlace(results[0]);
    } else {
        renderCandidateDropdown(results, "Multiple locations found. Select your destination:");
    }
}

function selectDestinationPlace(place) {
    selectedDestinationCoords = {
        lat: place.latitude,
        lon: place.longitude,
        name: place.place_name,
        address: place.display_address
    };

    const destInput = document.getElementById("destination");
    if (destInput) {
        destInput.value = place.place_name;
    }

    showSelectedPlaceInfo(place.place_name, place.display_address);

    const dropdown = document.getElementById("dest-results-dropdown");
    if (dropdown) dropdown.style.display = "none";
}

function showSelectedPlaceInfo(name, address) {
    const infoBadge = document.getElementById("selected-dest-info");
    if (!infoBadge) return;
    const icon = getPlaceTypeIcon("");
    infoBadge.innerHTML = `
        <div>${icon} <strong>Destination:</strong> ${name}</div>
        <small>📍 <strong>Location:</strong> ${address}</small>
    `;
    infoBadge.style.display = "flex";
}

function hideSelectedPlaceInfo() {
    const infoBadge = document.getElementById("selected-dest-info");
    if (infoBadge) {
        infoBadge.style.display = "none";
        infoBadge.innerHTML = "";
    }
}

function showSearchLoading() {
    const dropdown = document.getElementById("dest-results-dropdown");
    if (!dropdown) return;
    dropdown.innerHTML = `<div class="place-search-loading"><i class="fa-solid fa-spinner fa-spin"></i> Searching matching places...</div>`;
    dropdown.style.display = "block";
}

function showSearchError(msg) {
    const dropdown = document.getElementById("dest-results-dropdown");
    if (!dropdown) return;
    dropdown.innerHTML = `<div class="place-search-error"><i class="fa-solid fa-circle-exclamation"></i> ${msg}</div>`;
    dropdown.style.display = "block";
}

function getPlaceTypeIcon(type) {
    const t = (type || "").toLowerCase();
    if (t.includes("shop") || t.includes("supermarket") || t.includes("store") || t.includes("mall")) return "🏬";
    if (t.includes("restaurant") || t.includes("fast_food") || t.includes("cafe") || t.includes("food")) return "🍽️";
    if (t.includes("hospital") || t.includes("pharmacy") || t.includes("clinic")) return "🏥";
    if (t.includes("school") || t.includes("college") || t.includes("university")) return "🎓";
    if (t.includes("cinema") || t.includes("theatre")) return "🎬";
    return "🏪";
}

function renderCandidateDropdown(results, headerTitle = "Multiple locations found. Select your destination:") {
    const dropdown = document.getElementById("dest-results-dropdown");
    if (!dropdown) return;

    let html = `<div class="dropdown-header"><i class="fa-solid fa-layer-group text-sky"></i> ${headerTitle}</div>`;
    html += `<div class="dropdown-list">`;

    results.forEach((place, index) => {
        const icon = getPlaceTypeIcon(place.place_type);
        html += `
            <div class="place-result-item" data-index="${index}">
                <div class="result-title">${icon} ${place.place_name}</div>
                <div class="result-address">${place.display_address}</div>
            </div>
        `;
    });

    html += `</div>`;
    dropdown.innerHTML = html;
    dropdown.style.display = "block";

    const items = dropdown.querySelectorAll(".place-result-item");
    items.forEach(item => {
        item.addEventListener("click", () => {
            const idx = parseInt(item.getAttribute("data-index"), 10);
            if (!isNaN(idx) && results[idx]) {
                selectDestinationPlace(results[idx]);
            }
        });
    });
}

function initLeafletMap() {
    const mapElem = document.getElementById("map");
    if (!mapElem || typeof L === "undefined") return;

    try {
        // Ensure default Leaflet marker icons load cleanly from CDN
        if (L.Icon && L.Icon.Default && !L.Icon.Default.imagePathConfigured) {
            delete L.Icon.Default.prototype._getIconUrl;
            L.Icon.Default.mergeOptions({
                iconRetinaUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png",
                iconUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png",
                shadowUrl: "https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png"
            });
            L.Icon.Default.imagePathConfigured = true;
        }

        if (!leafletMap) {
            // Clean up any stale leaflet ID on DOM node if map variable was reset
            if (mapElem._leaflet_id) {
                mapElem._leaflet_id = null;
                mapElem.innerHTML = "";
            }

            const defaultCenter = [17.3850, 78.4867]; // Default: Hyderabad
            leafletMap = L.map("map", {
                center: defaultCenter,
                zoom: 8,
                zoomControl: true
            });

            const osmLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
                maxZoom: 19,
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            });

            osmLayer.on("tileerror", function (err) {
                console.warn("OpenStreetMap tile server loading notice:", err);
                const providerTag = document.getElementById("route-provider");
                if (providerTag && !providerTag.dataset.hasRouteError) {
                    providerTag.title = "OpenStreetMap tiles are loading slowly or offline.";
                }
            });

            osmLayer.addTo(leafletMap);
        }

        // Always invalidate map size if the container is currently visible
        if (mapElem.offsetWidth > 0 && mapElem.offsetHeight > 0) {
            leafletMap.invalidateSize(true);
        }

        const providerTag = document.getElementById("route-provider");
        if (providerTag && !providerTag.dataset.hasRouteError) {
            providerTag.textContent = "OSRM / OpenStreetMap";
        }
    } catch (err) {
        console.error("Error initializing Leaflet Map:", err);
    }
}

function setupDepartureTypeSelector() {
    const radioNow = document.getElementById("dep-now");
    const radioPlanned = document.getElementById("dep-planned");
    const plannedContainer = document.getElementById("planned-datetime-container");

    if (radioNow && radioPlanned) {
        radioNow.addEventListener("change", () => {
            departureOption = "NOW";
            if (plannedContainer) plannedContainer.style.display = "none";
            updateRadioStyles();
        });
        radioPlanned.addEventListener("change", () => {
            departureOption = "PLANNED";
            if (plannedContainer) plannedContainer.style.display = "grid";
            updateRadioStyles();
        });
    }
}

function updateRadioStyles() {
    const radioNow = document.getElementById("dep-now");
    const radioPlanned = document.getElementById("dep-planned");
    if (radioNow && radioNow.parentElement) {
        radioNow.parentElement.style.background = departureOption === "NOW" ? "rgba(59, 130, 246, 0.12)" : "rgba(255, 255, 255, 0.05)";
        radioNow.parentElement.style.borderColor = departureOption === "NOW" ? "rgba(59, 130, 246, 0.4)" : "rgba(255, 255, 255, 0.15)";
    }
    if (radioPlanned && radioPlanned.parentElement) {
        radioPlanned.parentElement.style.background = departureOption === "PLANNED" ? "rgba(59, 130, 246, 0.12)" : "rgba(255, 255, 255, 0.05)";
        radioPlanned.parentElement.style.borderColor = departureOption === "PLANNED" ? "rgba(59, 130, 246, 0.4)" : "rgba(255, 255, 255, 0.15)";
    }
}

function setupTravelModeSelector() {
    const modeButtons = document.querySelectorAll(".mode-btn");
    modeButtons.forEach(btn => {
        btn.addEventListener("click", () => {
            modeButtons.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");

            currentTravelMode = btn.getAttribute("data-mode") || "DRIVE";
            const hiddenInput = document.getElementById("travel_mode");
            if (hiddenInput) hiddenInput.value = currentTravelMode;

            const modeInfo = MODE_LABELS[currentTravelMode] || MODE_LABELS.DRIVE;
            const modeBadge = document.getElementById("res-mode-badge");
            if (modeBadge) modeBadge.textContent = modeInfo.tag;

            if (lastJourneySource && lastJourneyDest) {
                fetchAndDisplayRoute(lastJourneySource, lastJourneyDest, lastDepartureDate, lastDepartureTime, currentTravelMode, lastTrafficCondition);
            }
        });
    });
}

function setupTrafficConditionSelector() {
    const trafficSelect = document.getElementById("traffic_condition");
    if (trafficSelect) {
        trafficSelect.addEventListener("change", () => {
            lastTrafficCondition = trafficSelect.value;
            if (lastJourneySource && lastJourneyDest) {
                fetchAndDisplayRoute(lastJourneySource, lastJourneyDest, lastDepartureDate, lastDepartureTime, currentTravelMode, lastTrafficCondition);
                fetchAndDisplayMLPredictions(lastJourneySource, lastJourneyDest, lastDepartureDate, lastDepartureTime, lastTrafficCondition);
            }
        });
    }
}

function formatMinutesToHoursText(minutes) {
    if (!minutes || isNaN(minutes)) return "N/A";
    const mins = Math.round(minutes);
    const hrs = Math.floor(mins / 60);
    const remMins = mins % 60;
    if (hrs > 0) {
        return remMins > 0 ? `${hrs}h ${remMins.toString().padStart(2, '0')}m` : `${hrs}h`;
    }
    return `${mins} mins`;
}

function formatTimeToAMPM(timeStr) {
    if (!timeStr) return "09:00 AM";
    const parts = timeStr.split(":");
    let hours = parseInt(parts[0], 10);
    const minutes = parts[1] || "00";
    const ampm = hours >= 12 ? "PM" : "AM";
    hours = hours % 12;
    hours = hours ? hours : 12;
    const hoursStr = hours < 10 ? `0${hours}` : `${hours}`;
    return `${hoursStr}:${minutes} ${ampm}`;
}

function clearPreviousResults(source, destination) {
    const titleElem = document.getElementById("res-route-title");
    if (titleElem) {
        const cleanSource = source.replace(/📍\s*/g, '').split("(")[0].trim() || "Current Location";
        const cleanDest = destination.replace(/📍\s*/g, '').split("(")[0].trim();
        titleElem.innerHTML = `${cleanSource} <i class="fa-solid fa-arrow-right"></i> ${cleanDest}`;
    }

    const providerTag = document.getElementById("route-provider");
    if (providerTag) {
        delete providerTag.dataset.hasRouteError;
        providerTag.textContent = "OSRM / OpenStreetMap";
    }

    // Reset Result Box
    document.getElementById("res-google-duration").textContent = "Calculating...";
    document.getElementById("res-google-eta").textContent = "Calculating...";
    document.getElementById("res-departure-time").textContent = "--:--";
    document.getElementById("res-google-distance").textContent = "-- km";
    document.getElementById("res-weather").textContent = "Fetching...";
    document.getElementById("res-traffic").textContent = "Estimating...";
    document.getElementById("res-temp").textContent = "-- °C";
    document.getElementById("res-route-type").textContent = "--";

    // Clear Previous Leaflet Route & Markers from Map
    if (leafletMap) {
        if (currentRouteLayer) {
            leafletMap.removeLayer(currentRouteLayer);
            currentRouteLayer = null;
        }
        if (sourceMarker) {
            leafletMap.removeLayer(sourceMarker);
            sourceMarker = null;
        }
        if (destMarker) {
            leafletMap.removeLayer(destMarker);
            destMarker = null;
        }
        if (liveUserMarker) {
            leafletMap.removeLayer(liveUserMarker);
            liveUserMarker = null;
        }
    }

    // Stop running navigation and clear turn-by-turn guidance
    if (isNavigationActive || gpsWatchId !== null) {
        stopLiveNavigation();
    }
    currentActiveRoute = null;
    currentNavigationStepIndex = 0;
    lastUserPosition = null;

    const dirContainer = document.getElementById("route-directions-container");
    if (dirContainer) dirContainer.style.display = "none";
    const dirList = document.getElementById("directions-steps-list");
    if (dirList) dirList.innerHTML = "";
    const stepCountElem = document.getElementById("directions-step-count");
    if (stepCountElem) stepCountElem.textContent = "0 steps";
    const stepControls = document.getElementById("nav-step-nav-controls");
    if (stepControls) stepControls.style.display = "none";
}

function handleRouteCalculationError(errDetail) {
    if (isNavigationActive || gpsWatchId !== null) {
        stopLiveNavigation();
    }
    currentActiveRoute = null;
    currentNavigationStepIndex = 0;
    lastUserPosition = null;

    const dirContainer = document.getElementById("route-directions-container");
    if (dirContainer) dirContainer.style.display = "none";
    const dirList = document.getElementById("directions-steps-list");
    if (dirList) dirList.innerHTML = "";
    const stepControls = document.getElementById("nav-step-nav-controls");
    if (stepControls) stepControls.style.display = "none";

    initLeafletMap();
    if (leafletMap) {
        if (currentRouteLayer) {
            leafletMap.removeLayer(currentRouteLayer);
            currentRouteLayer = null;
        }
        if (sourceMarker) {
            leafletMap.removeLayer(sourceMarker);
            sourceMarker = null;
        }
        if (destMarker) {
            leafletMap.removeLayer(destMarker);
            destMarker = null;
        }
        if (liveUserMarker) {
            leafletMap.removeLayer(liveUserMarker);
            liveUserMarker = null;
        }
        leafletMap.invalidateSize(true);
    }
    const providerTag = document.getElementById("route-provider");
    if (providerTag) {
        providerTag.dataset.hasRouteError = "true";
        providerTag.innerHTML = '<span style="color: #f87171;"><i class="fa-solid fa-triangle-exclamation"></i> Route temporarily unavailable</span>';
    }
    const subtitleElem = document.getElementById("res-route-subtitle");
    if (subtitleElem) {
        subtitleElem.textContent = errDetail || "Route information is temporarily unavailable for this journey.";
    }
}

async function handleFormSubmit(e) {
    e.preventDefault();

    const rawSource = document.getElementById("source").value.trim();
    const destination = document.getElementById("destination").value.trim();
    const departure_date = document.getElementById("departure_date") ? document.getElementById("departure_date").value : new Date().toISOString().split("T")[0];
    const departure_time = document.getElementById("departure_time") ? document.getElementById("departure_time").value : "09:00";
    let traffic_condition = document.getElementById("traffic_condition") ? document.getElementById("traffic_condition").value : "Moderate";

    if (!rawSource || !destination) {
        alert("Please enter both starting location (From) and destination (To).");
        return;
    }

    let sourceForApi = rawSource;
    if (isUsingCurrentLocation && currentLocationCoords) {
        const cleanLocName = currentLocationName || "Current Location";
        sourceForApi = `${cleanLocName} (${currentLocationCoords.lat}, ${currentLocationCoords.lon})`;
    } else {
        sourceForApi = rawSource.replace(/📍\s*/g, '').trim();
    }

    // Resolve Destination Coordinates
    let destForApi = destination;
    if (selectedDestinationCoords && selectedDestinationCoords.lat && selectedDestinationCoords.lon) {
        destForApi = `${selectedDestinationCoords.name} (${selectedDestinationCoords.lat}, ${selectedDestinationCoords.lon})`;
    } else {
        showSearchLoading();
        const searchResults = await performPlaceSearch(destination);

        if (!searchResults || searchResults.length === 0) {
            showSearchError("Place not found. Try entering a more specific name or address.");
            return;
        }

        if (searchResults.length > 1) {
            renderCandidateDropdown(searchResults, "Multiple locations found. Select your destination:");
            return;
        }

        const singlePlace = searchResults[0];
        selectDestinationPlace(singlePlace);
        destForApi = `${singlePlace.place_name} (${singlePlace.latitude}, ${singlePlace.longitude})`;
    }

    if (sourceForApi.toLowerCase() === destForApi.toLowerCase()) {
        alert("Source and destination cannot be the same location!");
        return;
    }

    lastJourneySource = sourceForApi;
    lastJourneyDest = destForApi;
    lastDepartureDate = departure_date;
    lastDepartureTime = departure_time;
    lastTrafficCondition = traffic_condition;

    clearPreviousResults(rawSource, selectedDestinationCoords ? selectedDestinationCoords.name : destination);

    const predictBtn = document.getElementById("predict-btn");
    const originalBtnHTML = predictBtn.innerHTML;
    predictBtn.disabled = true;
    predictBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Calculating your journey...`;

    try {
        await Promise.all([
            fetchAndDisplayRoute(sourceForApi, destForApi, departure_date, departure_time, currentTravelMode, traffic_condition),
            fetchAndDisplayMLPredictions(sourceForApi, destForApi, departure_date, departure_time, traffic_condition)
        ]);

        const liveRouteSection = document.getElementById("live-route");
        if (liveRouteSection) {
            liveRouteSection.scrollIntoView({ behavior: "smooth" });
        }

        // Ensure Leaflet map size is updated after scrolling into view
        setTimeout(() => {
            if (leafletMap) {
                leafletMap.invalidateSize(true);
            }
        }, 300);

    } catch (err) {
        console.error("Form submit error:", err);
    } finally {
        predictBtn.disabled = false;
        predictBtn.innerHTML = originalBtnHTML;
    }
}

async function fetchAndDisplayRoute(source, destination, depDate, depTime, mode, trafficCondition) {
    let departure_datetime = "";
    let depTimeLabel = "";

    if (departureOption === "NOW") {
        const nowObj = new Date();
        departure_datetime = nowObj.toISOString();
        const hrs = nowObj.getHours();
        const mins = nowObj.getMinutes();
        depTimeLabel = `Now (${formatTimeToAMPM(`${hrs}:${mins}`)})`;
    } else {
        departure_datetime = `${depDate}T${depTime}:00`;
        depTimeLabel = formatTimeToAMPM(depTime);
    }

    const modeInfo = MODE_LABELS[mode] || MODE_LABELS.DRIVE;
    const modeBadge = document.getElementById("res-mode-badge");
    if (modeBadge) modeBadge.textContent = modeInfo.tag;

    document.getElementById("res-departure-time").textContent = depTimeLabel;
    document.getElementById("res-google-duration").textContent = "Calculating...";
    document.getElementById("res-google-eta").textContent = "Calculating...";

    try {
        const response = await fetch("/api/google-route", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                source: source,
                destination: destination,
                departure_datetime: departure_datetime,
                travel_mode: mode,
                traffic_condition: trafficCondition || lastTrafficCondition || "Moderate"
            })
        });

        const data = await response.json();

        if (!response.ok || !data.success || !data.google_route) {
            const errDetail = (data && data.detail) ? data.detail : "Route could not be calculated for the given locations.";
            document.getElementById("res-google-duration").textContent = "Unavailable";
            document.getElementById("res-google-eta").textContent = "N/A";
            document.getElementById("res-google-distance").textContent = "N/A";
            handleRouteCalculationError(errDetail);
            return;
        }

        const gr = data.google_route;
        currentActiveRoute = gr;

        const subtitleElem = document.getElementById("res-route-subtitle");
        if (subtitleElem) {
            subtitleElem.textContent = gr.provider ? `Calculated via ${gr.provider}` : "Real-time road travel duration computed by OSRM Routing Engine";
        }

        // 1. Primary Route Travel Time
        document.getElementById("res-google-duration").textContent = gr.duration_text || formatMinutesToHoursText(gr.duration_minutes);
        
        // 2. Departure Time & Calculated ETA
        document.getElementById("res-departure-time").textContent = gr.departure_time || depTimeLabel;
        document.getElementById("res-google-eta").textContent = gr.estimated_arrival_time || "N/A";

        // 3. Distance in km
        document.getElementById("res-google-distance").textContent = `${gr.distance_km} km`;

        // 4. Render Route on Leaflet Map
        renderLeafletMapRoute(gr);

        // 5. Render Turn-by-Turn Route Guidance Steps
        renderRouteDirections(gr.steps || []);

        // 6. Initialize Journey Metrics & Navigation Preview
        initializeNavigationPreview(gr);

        // 7. Automatically Save Trip to History for Authenticated User
        if (typeof saveCurrentTripToHistory === "function") {
            saveCurrentTripToHistory(
                gr.source,
                gr.destination,
                gr.distance_km,
                gr.duration_text || formatMinutesToHoursText(gr.duration_minutes),
                gr.traffic_condition || "Moderate",
                gr.departure_time || depTimeLabel,
                gr.estimated_arrival_time || "N/A"
            );
        }

    } catch (err) {
        console.error("Route fetch error:", err);
        document.getElementById("res-google-duration").textContent = "Unavailable";
        document.getElementById("res-google-eta").textContent = "N/A";
        document.getElementById("res-google-distance").textContent = "N/A";
        handleRouteCalculationError("Network or route service is temporarily unavailable.");
    }
}

async function fetchAndDisplayMLPredictions(source, destination, depDate, depTime, trafficCondition) {
    const departure_datetime = `${depDate}T${depTime}:00`;

    try {
        const response = await fetch("/api/predict", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                source: source,
                destination: destination,
                departure_datetime: departure_datetime,
                traffic_condition: trafficCondition
            })
        });

        if (!response.ok) {
            const errData = await response.json();
            throw new Error(errData.detail || "ML Prediction failed.");
        }

        const data = await response.json();
        if (!data.success) throw new Error(data.detail || "ML Prediction failed.");

        const conditions = data.travel_conditions;
        const prediction = data.prediction;
        const route = data.route;

        // Populate Weather & ML Traffic
        document.getElementById("res-weather").textContent = conditions.weather_condition;
        document.getElementById("res-temp").textContent = `${conditions.temperature_c} °C`;
        document.getElementById("res-traffic").textContent = conditions.traffic_condition;
        document.getElementById("res-route-type").textContent = route.route_type || "Highway";

    } catch (err) {
        console.error("ML Prediction fetch error:", err);
    }
}

function renderLeafletMapRoute(gr) {
    const mapElem = document.getElementById("map");
    if (!mapElem || typeof L === "undefined") return;

    if (!leafletMap) {
        initLeafletMap();
    }
    if (!leafletMap) return;

    // Reset provider tag to active state
    const providerTag = document.getElementById("route-provider");
    if (providerTag) {
        delete providerTag.dataset.hasRouteError;
        providerTag.textContent = gr.provider || "OSRM / OpenStreetMap";
    }

    // Always invalidate container size when rendering route
    leafletMap.invalidateSize(true);

    // Clear previous layers
    if (currentRouteLayer) {
        leafletMap.removeLayer(currentRouteLayer);
        currentRouteLayer = null;
    }
    if (sourceMarker) {
        leafletMap.removeLayer(sourceMarker);
        sourceMarker = null;
    }
    if (destMarker) {
        leafletMap.removeLayer(destMarker);
        destMarker = null;
    }

    // Validate geometry
    const rawGeometry = Array.isArray(gr.route_geometry) ? gr.route_geometry : [];
    const validGeometry = rawGeometry.filter(pt =>
        Array.isArray(pt) && pt.length >= 2 &&
        typeof pt[0] === "number" && !isNaN(pt[0]) &&
        typeof pt[1] === "number" && !isNaN(pt[1])
    );

    const hasSourceCoords = Array.isArray(gr.source_coordinates) && gr.source_coordinates.length >= 2 &&
        typeof gr.source_coordinates[0] === "number" && !isNaN(gr.source_coordinates[0]) &&
        typeof gr.source_coordinates[1] === "number" && !isNaN(gr.source_coordinates[1]);

    const hasDestCoords = Array.isArray(gr.destination_coordinates) && gr.destination_coordinates.length >= 2 &&
        typeof gr.destination_coordinates[0] === "number" && !isNaN(gr.destination_coordinates[0]) &&
        typeof gr.destination_coordinates[1] === "number" && !isNaN(gr.destination_coordinates[1]);

    let startPt = null;
    let endPt = null;

    if (validGeometry.length >= 2) {
        startPt = validGeometry[0];
        endPt = validGeometry[validGeometry.length - 1];
    } else if (hasSourceCoords && hasDestCoords) {
        startPt = gr.source_coordinates;
        endPt = gr.destination_coordinates;
    }

    if (!startPt || !endPt) {
        console.warn("Valid route coordinates could not be determined for map display.");
        if (providerTag) {
            providerTag.innerHTML = '<span style="color: #f87171;"><i class="fa-solid fa-triangle-exclamation"></i> Coordinates unavailable</span>';
        }
        return;
    }

    // Place source and destination markers with distinct, clear styles
    const sourceLabel = gr.source || "Origin";
    const destLabel = gr.destination || "Destination";

    const sourceIcon = L.divIcon({
        className: 'custom-route-marker source-route-pin',
        html: '<i class="fa-solid fa-play" style="font-size:12px;margin-left:2px;"></i>',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
        popupAnchor: [0, -14]
    });

    const destIcon = L.divIcon({
        className: 'custom-route-marker dest-route-pin',
        html: '<i class="fa-solid fa-flag-checkered" style="font-size:12px;"></i>',
        iconSize: [28, 28],
        iconAnchor: [14, 14],
        popupAnchor: [0, -14]
    });

    sourceMarker = L.marker(startPt, { icon: sourceIcon }).addTo(leafletMap).bindPopup(`<b>From:</b> ${sourceLabel}`);
    destMarker = L.marker(endPt, { icon: destIcon }).addTo(leafletMap).bindPopup(`<b>To:</b> ${destLabel}`);

    let fitTarget = null;

    if (validGeometry.length >= 2) {
        currentRouteLayer = L.polyline(validGeometry, {
            color: "#2563eb",
            weight: 6,
            opacity: 0.9,
            lineJoin: "round",
            lineCap: "round"
        }).addTo(leafletMap);
        fitTarget = currentRouteLayer.getBounds();
    } else {
        fitTarget = L.latLngBounds([startPt, endPt]);
    }

    // Safe fitBounds function that invalidates size and guards against zero-dimension scale bugs
    function fitRouteToView() {
        if (!leafletMap) return;
        leafletMap.invalidateSize(true);
        if (fitTarget && fitTarget.isValid()) {
            const size = leafletMap.getSize();
            if (size.x > 80 && size.y > 80) {
                leafletMap.fitBounds(fitTarget, { padding: [40, 40], maxZoom: 16 });
            } else if (size.x > 20 && size.y > 20) {
                leafletMap.fitBounds(fitTarget, { padding: [10, 10], maxZoom: 16 });
            } else {
                leafletMap.setView(fitTarget.getCenter(), 8);
            }
        }
    }

    fitRouteToView();
    // Schedule size invalidation and fitBounds after layout settles and after scroll
    setTimeout(fitRouteToView, 150);
    setTimeout(fitRouteToView, 350);
}

/* ==================================================
 * LIVE NAVIGATION ENGINE & ROUTE GUIDANCE LOGIC
 * ================================================== */
let currentActiveRoute = null;
let isNavigationActive = false;
let currentNavigationStepIndex = 0;
let gpsWatchId = null;
let liveUserMarker = null;
let lastUserPosition = null;
let isRecalculatingRoute = false;
let lastRecalculateTimestamp = 0;

function escapeHtml(str) {
    if (!str) return "";
    return String(str)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

function calculateCompassBearing(lat1, lon1, lat2, lon2) {
    const phi1 = lat1 * Math.PI / 180;
    const phi2 = lat2 * Math.PI / 180;
    const deltaLambda = (lon2 - lon1) * Math.PI / 180;
    const y = Math.sin(deltaLambda) * Math.cos(phi2);
    const x = Math.cos(phi1) * Math.sin(phi2) - Math.sin(phi1) * Math.cos(phi2) * Math.cos(deltaLambda);
    const bearing = Math.atan2(y, x) * 180 / Math.PI;
    return (bearing + 360) % 360;
}

function getManeuverIcon(maneuverType, maneuverModifier) {
    const type = (maneuverType || "").toLowerCase();
    const mod = (maneuverModifier || "").toLowerCase();

    if (type === "depart") return '<i class="fa-solid fa-location-arrow"></i>';
    if (type === "arrive") return '<i class="fa-solid fa-flag-checkered"></i>';
    if (mod === "uturn") return '<i class="fa-solid fa-rotate-left"></i>';
    if (type.includes("roundabout") || mod.includes("roundabout")) return '<i class="fa-solid fa-arrows-rotate"></i>';
    if (type === "fork" || type.includes("ramp") || type === "exit") {
        if (mod.includes("left")) return '<i class="fa-solid fa-code-fork fa-flip-horizontal"></i>';
        return '<i class="fa-solid fa-code-fork"></i>';
    }
    if (mod === "sharp left") return '<i class="fa-solid fa-arrow-turn-down fa-flip-horizontal"></i>';
    if (mod === "sharp right") return '<i class="fa-solid fa-arrow-turn-down"></i>';
    if (mod === "slight left" || mod === "bear left") return '<i class="fa-solid fa-arrow-trend-up fa-flip-horizontal"></i>';
    if (mod === "slight right" || mod === "bear right") return '<i class="fa-solid fa-arrow-trend-up"></i>';
    if (mod === "left") return '<i class="fa-solid fa-arrow-left"></i>';
    if (mod === "right") return '<i class="fa-solid fa-arrow-right"></i>';
    return '<i class="fa-solid fa-arrow-up"></i>';
}

function renderRouteDirections(steps) {
    const dirContainer = document.getElementById("route-directions-container");
    const dirList = document.getElementById("directions-steps-list");
    const stepCountElem = document.getElementById("directions-step-count");

    if (!dirContainer || !dirList) return;

    if (!Array.isArray(steps) || steps.length === 0) {
        dirContainer.style.display = "none";
        dirList.innerHTML = "";
        return;
    }

    dirContainer.style.display = "block";
    if (stepCountElem) {
        stepCountElem.textContent = `${steps.length} ${steps.length === 1 ? 'step' : 'steps'}`;
    }

    dirList.innerHTML = "";
    steps.forEach((step, idx) => {
        const item = document.createElement("div");
        item.className = `direction-step-item ${idx === currentNavigationStepIndex ? 'active-step' : ''}`;
        item.dataset.stepIndex = idx;

        const iconHtml = getManeuverIcon(step.maneuver_type, step.maneuver_modifier);
        const distBadge = step.distance_text && step.distance_meters > 0 ? 
            `<span class="step-dist-badge"><i class="fa-solid fa-route"></i> ${step.distance_text}</span>` : '';
        const roadBadge = step.road_name ? 
            `<span class="step-road-badge"><i class="fa-solid fa-road"></i> ${escapeHtml(step.road_name)}</span>` : '';

        item.innerHTML = `
            <div class="step-icon-col">${iconHtml}</div>
            <div class="step-content-col">
                <div class="step-instruction">${escapeHtml(step.instruction)}</div>
                <div class="step-meta">
                    ${distBadge}
                    ${roadBadge}
                </div>
            </div>
        `;

        item.addEventListener("click", () => {
            selectNavigationStep(idx, true);
        });

        dirList.appendChild(item);
    });
}

function selectNavigationStep(idx, centerMap = true) {
    if (!currentActiveRoute || !currentActiveRoute.steps || idx < 0 || idx >= currentActiveRoute.steps.length) return;
    currentNavigationStepIndex = idx;
    const step = currentActiveRoute.steps[idx];

    // Highlight in directions list
    const items = document.querySelectorAll(".direction-step-item");
    items.forEach((it, i) => {
        if (i === idx) {
            it.classList.add("active-step");
            it.scrollIntoView({ behavior: "smooth", block: "nearest" });
        } else {
            it.classList.remove("active-step");
        }
    });

    // Update prompt display
    const instrElem = document.getElementById("nav-next-instruction");
    const distElem = document.getElementById("nav-next-distance");
    const indicatorElem = document.getElementById("nav-step-indicator");

    if (instrElem) instrElem.textContent = step.instruction;
    if (distElem) distElem.textContent = step.distance_text || "-- m";
    if (indicatorElem) indicatorElem.textContent = `Step ${idx + 1} of ${currentActiveRoute.steps.length}`;

    // Pan map to step location
    if (centerMap && leafletMap && step.location && step.location.length === 2 && step.location[0] && step.location[1]) {
        leafletMap.panTo(step.location, { animate: true, duration: 0.5 });
    }
}

function initializeNavigationPreview(gr) {
    currentNavigationStepIndex = 0;
    const steps = gr.steps || [];

    const remDistElem = document.getElementById("nav-rem-distance");
    const remTimeElem = document.getElementById("nav-rem-time");
    const etaElem = document.getElementById("nav-eta");
    const instrElem = document.getElementById("nav-next-instruction");
    const turnDistElem = document.getElementById("nav-next-distance");
    const indicatorElem = document.getElementById("nav-step-indicator");

    if (remDistElem) remDistElem.textContent = `${gr.distance_km} km`;
    if (remTimeElem) remTimeElem.textContent = gr.duration_text || formatMinutesToHoursText(gr.duration_minutes);
    if (etaElem) etaElem.textContent = gr.estimated_arrival_time || "--:--";

    if (steps.length > 0) {
        const firstStep = steps[0];
        if (instrElem) instrElem.textContent = firstStep.instruction;
        if (turnDistElem) turnDistElem.textContent = firstStep.distance_text || formatDistanceMetersOrKm(firstStep.distance_meters || 0);
        if (indicatorElem) indicatorElem.textContent = `Step 1 of ${steps.length}`;
    }
}

function setupNavigationHandlers() {
    const startBtn = document.getElementById("start-nav-btn");
    const stopBtn = document.getElementById("stop-nav-btn");
    const prevBtn = document.getElementById("nav-prev-step-btn");
    const nextBtn = document.getElementById("nav-next-step-btn");

    if (startBtn) {
        startBtn.addEventListener("click", startLiveNavigation);
    }
    if (stopBtn) {
        stopBtn.addEventListener("click", stopLiveNavigation);
    }
    if (prevBtn) {
        prevBtn.addEventListener("click", () => {
            if (!currentActiveRoute || !currentActiveRoute.steps) return;
            const newIdx = Math.max(0, currentNavigationStepIndex - 1);
            selectNavigationStep(newIdx, true);
        });
    }
    if (nextBtn) {
        nextBtn.addEventListener("click", () => {
            if (!currentActiveRoute || !currentActiveRoute.steps) return;
            const newIdx = Math.min(currentActiveRoute.steps.length - 1, currentNavigationStepIndex + 1);
            selectNavigationStep(newIdx, true);
        });
    }
}

function startLiveNavigation() {
    if (!currentActiveRoute || !currentActiveRoute.route_geometry || currentActiveRoute.route_geometry.length === 0) {
        alert("Please calculate a trip route first before starting live navigation.");
        return;
    }

    isNavigationActive = true;
    currentNavigationStepIndex = 0;

    // Toggle Action Bar vs Navigation Mode Container
    const navActionBar = document.getElementById("nav-action-bar");
    const navModeContainer = document.getElementById("navigation-mode-container");
    const reachedCard = document.getElementById("nav-reached-card");
    const offRouteAlert = document.getElementById("nav-offroute-alert");
    const gpsAlert = document.getElementById("nav-gps-alert");
    const turnCard = document.getElementById("nav-turn-card");
    const stepControls = document.getElementById("nav-step-nav-controls");

    if (navActionBar) navActionBar.style.display = "none";
    if (navModeContainer) navModeContainer.style.display = "flex";
    if (reachedCard) reachedCard.style.display = "none";
    if (offRouteAlert) offRouteAlert.style.display = "none";
    if (gpsAlert) gpsAlert.style.display = "none";
    if (turnCard) turnCard.style.display = "flex";

    const modeInfo = MODE_LABELS[currentTravelMode] || MODE_LABELS.DRIVE;
    const activeLabel = document.getElementById("nav-active-mode-label");
    if (activeLabel) {
        activeLabel.textContent = `${modeInfo.emoji} Navigation Active`;
    }

    // Initialize metrics display from full route data
    initializeNavigationPreview(currentActiveRoute);

    if (!navigator.geolocation) {
        showNavigationAlert("Location service is not supported by your browser. Manual step guidance is available below.", "warning");
        if (stepControls) stepControls.style.display = "flex";
        return;
    }

    // Start watching position continuously
    gpsWatchId = navigator.geolocation.watchPosition(
        onGpsPositionUpdate,
        onGpsPositionError,
        {
            enableHighAccuracy: true,
            timeout: 10000,
            maximumAge: 0
        }
    );
}

function stopLiveNavigation() {
    if (gpsWatchId !== null) {
        navigator.geolocation.clearWatch(gpsWatchId);
        gpsWatchId = null;
    }

    isNavigationActive = false;
    currentNavigationStepIndex = 0;
    lastUserPosition = null;

    // Remove User Location Marker from Map
    if (leafletMap && liveUserMarker) {
        leafletMap.removeLayer(liveUserMarker);
        liveUserMarker = null;
    }

    // Switch UI back to normal route view
    const navActionBar = document.getElementById("nav-action-bar");
    const navModeContainer = document.getElementById("navigation-mode-container");
    const stepControls = document.getElementById("nav-step-nav-controls");
    const offRouteAlert = document.getElementById("nav-offroute-alert");
    const gpsAlert = document.getElementById("nav-gps-alert");
    const reachedCard = document.getElementById("nav-reached-card");

    if (navModeContainer) navModeContainer.style.display = "none";
    if (navActionBar) navActionBar.style.display = "block";
    if (stepControls) stepControls.style.display = "none";
    if (offRouteAlert) offRouteAlert.style.display = "none";
    if (gpsAlert) gpsAlert.style.display = "none";
    if (reachedCard) reachedCard.style.display = "none";
}

function onGpsPositionError(error) {
    console.warn("GPS Navigation Position Notice:", error);
    const gpsAlert = document.getElementById("nav-gps-alert");
    const alertText = document.getElementById("nav-gps-alert-text");
    const stepControls = document.getElementById("nav-step-nav-controls");

    if (stepControls) stepControls.style.display = "flex";

    if (gpsAlert && alertText) {
        if (error.code === error.PERMISSION_DENIED) {
            alertText.textContent = "Location permission is required for live navigation. Step-by-step guidance is available below.";
        } else {
            alertText.textContent = "GPS signal weak or unavailable. Step-by-step guidance remains active below.";
        }
        gpsAlert.className = "nav-alert-banner warning";
        gpsAlert.style.display = "flex";
    }
}

function showNavigationAlert(msg, type = "warning") {
    const gpsAlert = document.getElementById("nav-gps-alert");
    const alertText = document.getElementById("nav-gps-alert-text");
    if (gpsAlert && alertText) {
        alertText.textContent = msg;
        gpsAlert.className = `nav-alert-banner ${type}`;
        gpsAlert.style.display = "flex";
    }
}

function formatDistanceMetersOrKm(meters) {
    if (meters < 1000) {
        return `${Math.round(meters)} m`;
    }
    const km = (meters / 1000.0).toFixed(1);
    return `${km} km`;
}

function getHaversineDistanceMeters(lat1, lon1, lat2, lon2) {
    const R = 6371000;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLon = (lon2 - lon1) * Math.PI / 180;
    const a = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLon / 2) * Math.sin(dLon / 2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
    return R * c;
}

function projectPointOnSegment(pLat, pLon, aLat, aLon, bLat, bLon) {
    const dLat = bLat - aLat;
    const dLon = bLon - aLon;
    const lenSq = dLat * dLat + dLon * dLon;

    if (lenSq === 0) {
        return { lat: aLat, lon: aLon, t: 0 };
    }

    let t = ((pLat - aLat) * dLat + (pLon - aLon) * dLon) / lenSq;
    t = Math.max(0, Math.min(1, t));

    return {
        lat: aLat + t * dLat,
        lon: aLon + t * dLon,
        t: t
    };
}

function onGpsPositionUpdate(position) {
    if (!isNavigationActive || !currentActiveRoute || !currentActiveRoute.route_geometry) return;

    const userLat = position.coords.latitude;
    const userLon = position.coords.longitude;
    const accuracy = position.coords.accuracy || 0;
    const deviceHeading = typeof position.coords.heading === "number" && !isNaN(position.coords.heading) ? position.coords.heading : null;

    // 1. Accuracy Check
    const gpsAlert = document.getElementById("nav-gps-alert");
    const alertText = document.getElementById("nav-gps-alert-text");
    const stepControls = document.getElementById("nav-step-nav-controls");

    if (accuracy > 70) {
        if (gpsAlert && alertText) {
            alertText.textContent = `GPS accuracy is approximate (${Math.round(accuracy)}m).`;
            gpsAlert.style.display = "flex";
        }
    } else {
        if (gpsAlert) gpsAlert.style.display = "none";
    }
    if (stepControls) stepControls.style.display = "none";

    // 2. Update Live Marker on Leaflet Map
    if (leafletMap) {
        if (!liveUserMarker) {
            const pulseIcon = L.divIcon({
                className: 'live-gps-user-marker',
                html: '<div class="live-user-pulse"></div>',
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            });
            liveUserMarker = L.marker([userLat, userLon], { icon: pulseIcon }).addTo(leafletMap);
        } else {
            liveUserMarker.setLatLng([userLat, userLon]);
        }
        leafletMap.panTo([userLat, userLon], { animate: true, duration: 0.5 });
    }

    // 3. Destination Reached Check (threshold = 30 meters)
    const routeGeom = currentActiveRoute.route_geometry;
    const destPt = routeGeom[routeGeom.length - 1];
    const distToDestMeters = getHaversineDistanceMeters(userLat, userLon, destPt[0], destPt[1]);

    if (distToDestMeters <= 30) {
        handleDestinationReached();
        return;
    }

    // 4. Calculate User Position relative to Route Geometry
    let minDistMeters = Infinity;
    let bestSegIdx = 0;
    let projPoint = { lat: routeGeom[0][0], lon: routeGeom[0][1] };

    for (let i = 0; i < routeGeom.length - 1; i++) {
        const segStart = routeGeom[i];
        const segEnd = routeGeom[i + 1];
        const proj = projectPointOnSegment(userLat, userLon, segStart[0], segStart[1], segEnd[0], segEnd[1]);
        const distToProj = getHaversineDistanceMeters(userLat, userLon, proj.lat, proj.lon);

        if (distToProj < minDistMeters) {
            minDistMeters = distToProj;
            bestSegIdx = i;
            projPoint = proj;
        }
    }

    // 5. Off-Route Detection (threshold = 75 meters)
    const offRouteAlert = document.getElementById("nav-offroute-alert");
    if (minDistMeters > 75) {
        if (offRouteAlert) offRouteAlert.style.display = "flex";

        // Trigger route recalculation if not already recalculating (throttled 8s)
        const nowMs = Date.now();
        if (!isRecalculatingRoute && (nowMs - lastRecalculateTimestamp > 8000)) {
            recalculateRouteFromCurrentLocation(userLat, userLon);
        }
        return;
    } else {
        if (offRouteAlert) offRouteAlert.style.display = "none";
    }

    // 6. Calculate Remaining Distance Along Route Geometry
    let remainingMeters = getHaversineDistanceMeters(projPoint.lat, projPoint.lon, routeGeom[bestSegIdx + 1][0], routeGeom[bestSegIdx + 1][1]);
    for (let k = bestSegIdx + 1; k < routeGeom.length - 1; k++) {
        remainingMeters += getHaversineDistanceMeters(routeGeom[k][0], routeGeom[k][1], routeGeom[k + 1][0], routeGeom[k + 1][1]);
    }

    const remainingKm = Math.max(0.1, remainingMeters / 1000.0);

    // 7. Calculate Remaining Travel Time & Dynamic ETA
    const totalDistKm = currentActiveRoute.distance_km || 1.0;
    const totalDurationMins = currentActiveRoute.duration_minutes || 1.0;
    const minutesPerKm = totalDistKm > 0 ? (totalDurationMins / totalDistKm) : 1.5;

    const remDurationMins = Math.max(1, Math.round(remainingKm * minutesPerKm));

    const nowObj = new Date();
    const etaDate = new Date(nowObj.getTime() + remDurationMins * 60 * 1000);
    const etaHrs = etaDate.getHours();
    const etaMins = etaDate.getMinutes();
    const etaStr = formatTimeToAMPM(`${etaHrs}:${etaMins}`);

    // 8. Maneuver Advancement & Next Turn Distance Calculation
    const steps = currentActiveRoute.steps || [];
    let nextTurnInstruction = "Continue on your route";
    let distToNextTurnMeters = remainingMeters;

    if (steps.length > 0) {
        // Advance step if user reached or passed current target step location
        while (currentNavigationStepIndex < steps.length - 1) {
            const currentStep = steps[currentNavigationStepIndex];
            const stepLoc = currentStep.location;
            if (stepLoc && stepLoc.length === 2 && stepLoc[0] && stepLoc[1]) {
                const distToManeuver = getHaversineDistanceMeters(userLat, userLon, stepLoc[0], stepLoc[1]);
                if (distToManeuver <= 25) {
                    // Turn passed / completed: advance to next step
                    currentNavigationStepIndex++;
                    continue;
                }
            }
            break;
        }

        const activeStep = steps[currentNavigationStepIndex];
        if (activeStep) {
            nextTurnInstruction = activeStep.instruction;
            const targetLoc = activeStep.location;
            if (targetLoc && targetLoc.length === 2 && targetLoc[0] && targetLoc[1]) {
                distToNextTurnMeters = getHaversineDistanceMeters(userLat, userLon, targetLoc[0], targetLoc[1]);
            } else {
                distToNextTurnMeters = remainingMeters;
            }
        }

        // Highlight active step in directions list
        const items = document.querySelectorAll(".direction-step-item");
        items.forEach((it, i) => {
            if (i === currentNavigationStepIndex) {
                it.classList.add("active-step");
                it.scrollIntoView({ behavior: "smooth", block: "nearest" });
            } else {
                it.classList.remove("active-step");
            }
        });
    }

    // 9. Update Compass Direction / Bearing
    const compassIcon = document.getElementById("nav-compass-icon");
    if (compassIcon) {
        let headingDeg = null;
        if (deviceHeading !== null) {
            headingDeg = deviceHeading;
        } else if (lastUserPosition) {
            headingDeg = calculateCompassBearing(lastUserPosition[0], lastUserPosition[1], userLat, userLon);
        }
        if (headingDeg !== null) {
            compassIcon.style.transform = `rotate(${Math.round(headingDeg)}deg)`;
            compassIcon.title = `Heading ${Math.round(headingDeg)}°`;
        }
    }

    lastUserPosition = [userLat, userLon];

    // 10. Update Navigation UI Display
    const instrElem = document.getElementById("nav-next-instruction");
    const turnDistElem = document.getElementById("nav-next-distance");
    const remDistElem = document.getElementById("nav-rem-distance");
    const remTimeElem = document.getElementById("nav-rem-time");
    const etaElem = document.getElementById("nav-eta");
    const indicatorElem = document.getElementById("nav-step-indicator");

    if (instrElem) instrElem.textContent = nextTurnInstruction;
    if (turnDistElem) turnDistElem.textContent = formatDistanceMetersOrKm(distToNextTurnMeters);
    if (remDistElem) remDistElem.textContent = formatDistanceMetersOrKm(remainingMeters);
    if (remTimeElem) remTimeElem.textContent = formatMinutesToHoursText(remDurationMins);
    if (etaElem) etaElem.textContent = etaStr;
    if (indicatorElem && steps.length > 0) {
        indicatorElem.textContent = `Step ${currentNavigationStepIndex + 1} of ${steps.length}`;
    }
}

function handleDestinationReached() {
    if (gpsWatchId !== null) {
        navigator.geolocation.clearWatch(gpsWatchId);
        gpsWatchId = null;
    }

    const reachedCard = document.getElementById("nav-reached-card");
    const turnCard = document.getElementById("nav-turn-card");
    const offRouteAlert = document.getElementById("nav-offroute-alert");

    if (reachedCard) reachedCard.style.display = "flex";
    if (turnCard) turnCard.style.display = "none";
    if (offRouteAlert) offRouteAlert.style.display = "none";

    const remDistElem = document.getElementById("nav-rem-distance");
    const remTimeElem = document.getElementById("nav-rem-time");
    const etaElem = document.getElementById("nav-eta");

    if (remDistElem) remDistElem.textContent = "0 m";
    if (remTimeElem) remTimeElem.textContent = "0 min";
    if (etaElem) etaElem.textContent = "Arrived";
}

async function recalculateRouteFromCurrentLocation(userLat, userLon) {
    if (isRecalculatingRoute || !currentActiveRoute) return;

    isRecalculatingRoute = true;
    lastRecalculateTimestamp = Date.now();

    const currentLocStr = `Current Location (${userLat.toFixed(5)}, ${userLon.toFixed(5)})`;
    const destination = currentActiveRoute.destination;

    try {
        const response = await fetch("/api/google-route", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                source: currentLocStr,
                destination: destination,
                departure_datetime: new Date().toISOString(),
                travel_mode: currentTravelMode,
                traffic_condition: lastTrafficCondition
            })
        });

        if (response.ok) {
            const data = await response.json();
            if (data && data.success && data.google_route) {
                currentActiveRoute = data.google_route;
                currentNavigationStepIndex = 0;

                // Update polyline on map
                if (leafletMap && currentRouteLayer) {
                    currentRouteLayer.setLatLngs(data.google_route.route_geometry);
                }

                // Update directions list
                renderRouteDirections(data.google_route.steps || []);

                // Update preview
                initializeNavigationPreview(data.google_route);

                const offRouteAlert = document.getElementById("nav-offroute-alert");
                if (offRouteAlert) offRouteAlert.style.display = "none";
            }
        }
    } catch (err) {
        console.warn("Recalculate route notice:", err);
    } finally {
        isRecalculatingRoute = false;
    }
}

