/* WayVista — User Authentication & Dashboard Manager */
const AUTH_TOKEN_KEY = "wayvista_auth_token";
const AUTH_USER_KEY = "wayvista_auth_user";

let currentUser = null;
let currentToken = null;
let unverifiedEmail = "";

document.addEventListener("DOMContentLoaded", () => {
    initAuthApp();
});

function initAuthApp() {
    // 1. Check existing session token
    currentToken = localStorage.getItem(AUTH_TOKEN_KEY) || sessionStorage.getItem(AUTH_TOKEN_KEY);
    const savedUserStr = localStorage.getItem(AUTH_USER_KEY) || sessionStorage.getItem(AUTH_USER_KEY);

    if (savedUserStr) {
        try {
            currentUser = JSON.parse(savedUserStr);
        } catch (e) {
            currentUser = null;
        }
    }

    // 2. Attach Event Listeners for Forms & Navigation
    setupAuthFormListeners();
    setupDashboardNavListeners();

    // 3. Validate Token with Backend
    if (currentToken) {
        validateSessionToken();
    } else {
        showView("login");
    }
}

async function validateSessionToken() {
    try {
        const response = await fetch("/api/auth/me", {
            headers: {
                "Authorization": `Bearer ${currentToken}`
            }
        });

        if (response.ok) {
            const data = await response.json();
            if (data && data.success && data.user) {
                currentUser = data.user;
                saveSession(currentToken, currentUser, true);
                updateNavbarUI(true);
                showView("dashboard");
                return;
            }
        }
    } catch (e) {
        console.warn("Session validation notice:", e);
    }

    // Token invalid or expired
    clearSession();
    showView("login");
}

function saveSession(token, user, remember = true) {
    currentToken = token;
    currentUser = user;
    const storage = remember ? localStorage : sessionStorage;
    storage.setItem(AUTH_TOKEN_KEY, token);
    storage.setItem(AUTH_USER_KEY, JSON.stringify(user));
}

function clearSession() {
    currentToken = null;
    currentUser = null;
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    sessionStorage.removeItem(AUTH_TOKEN_KEY);
    sessionStorage.removeItem(AUTH_USER_KEY);
    updateNavbarUI(false);
}

/* ==================================================
 * VIEW SWITCHER & ROUTER
 * ================================================== */
function showView(viewName) {
    const authContainer = document.getElementById("auth-container");
    const loginCard = document.getElementById("login-card");
    const registerCard = document.getElementById("register-card");
    const verifyCard = document.getElementById("verify-card");
    const dashboardCard = document.getElementById("dashboard-card");
    const tripsCard = document.getElementById("trips-card");
    const profileCard = document.getElementById("profile-card");
    const mainTravelApp = document.getElementById("main-travel-app");
    const heroSection = document.getElementById("hero-section");

    // Hide all view containers
    if (loginCard) loginCard.style.display = "none";
    if (registerCard) registerCard.style.display = "none";
    if (verifyCard) verifyCard.style.display = "none";
    if (dashboardCard) dashboardCard.style.display = "none";
    if (tripsCard) tripsCard.style.display = "none";
    if (profileCard) profileCard.style.display = "none";
    if (mainTravelApp) mainTravelApp.style.display = "none";
    if (heroSection) heroSection.style.display = "none";

    // Clear alert boxes
    hideAuthAlerts();

    // Check authorization for protected views
    const isProtected = ["dashboard", "planner", "navigation", "trips", "profile"].includes(viewName);
    if (isProtected && (!currentUser || !currentToken)) {
        showView("login");
        showAuthAlert("login", "Please log in to access the WayVista application.", "warning");
        return;
    }

    if (viewName === "login") {
        if (authContainer) authContainer.style.display = "block";
        if (loginCard) loginCard.style.display = "block";
        if (heroSection) heroSection.style.display = "block";
        updateNavbarUI(false);
    } else if (viewName === "register") {
        if (authContainer) authContainer.style.display = "block";
        if (registerCard) registerCard.style.display = "block";
        if (heroSection) heroSection.style.display = "block";
        updateNavbarUI(false);
    } else if (viewName === "verify") {
        if (authContainer) authContainer.style.display = "block";
        if (verifyCard) verifyCard.style.display = "block";
        if (heroSection) heroSection.style.display = "block";
        const emailSpan = document.getElementById("verify-email-display");
        if (emailSpan) emailSpan.textContent = unverifiedEmail || "your email";
        updateNavbarUI(false);
    } else if (viewName === "dashboard") {
        if (authContainer) authContainer.style.display = "block";
        if (dashboardCard) dashboardCard.style.display = "block";
        if (heroSection) heroSection.style.display = "block";
        updateNavbarUI(true);
        updateDashboardUserGreeting();
    } else if (viewName === "planner" || viewName === "navigation") {
        if (authContainer) authContainer.style.display = "none";
        if (heroSection) heroSection.style.display = "block";
        if (mainTravelApp) mainTravelApp.style.display = "block";
        updateNavbarUI(true);

        if (viewName === "navigation") {
            const liveRouteSec = document.getElementById("live-route");
            if (liveRouteSec) liveRouteSec.scrollIntoView({ behavior: "smooth" });
        } else {
            const plannerSec = document.getElementById("planner");
            if (plannerSec) plannerSec.scrollIntoView({ behavior: "smooth" });
        }

        // Ensure Leaflet map recalculates its dimensions after container becomes visible
        setTimeout(() => {
            if (typeof initLeafletMap === "function") {
                initLeafletMap();
            }
            if (typeof leafletMap !== "undefined" && leafletMap) {
                leafletMap.invalidateSize(true);
            }
        }, 150);
    } else if (viewName === "trips") {
        if (authContainer) authContainer.style.display = "block";
        if (tripsCard) tripsCard.style.display = "block";
        if (heroSection) heroSection.style.display = "none";
        updateNavbarUI(true);
        loadUserTripsHistory();
    } else if (viewName === "profile") {
        if (authContainer) authContainer.style.display = "block";
        if (profileCard) profileCard.style.display = "block";
        if (heroSection) heroSection.style.display = "none";
        updateNavbarUI(true);
        loadUserProfileData();
    }
}

function updateNavbarUI(isLoggedIn) {
    const loggedOutNav = document.getElementById("logged-out-nav");
    const loggedInNav = document.getElementById("logged-in-nav");

    if (isLoggedIn && currentUser) {
        if (loggedOutNav) loggedOutNav.style.display = "none";
        if (loggedInNav) loggedInNav.style.display = "flex";
    } else {
        if (loggedOutNav) loggedOutNav.style.display = "flex";
        if (loggedInNav) loggedInNav.style.display = "none";
    }
}

function updateDashboardUserGreeting() {
    const nameElem = document.getElementById("dash-user-name");
    if (nameElem && currentUser) {
        nameElem.textContent = currentUser.name || "Traveler";
    }
}

/* ==================================================
 * AUTHENTICATION FORM HANDLERS
 * ================================================== */
function setupAuthFormListeners() {
    // Login Form
    const loginForm = document.getElementById("login-form");
    if (loginForm) {
        loginForm.addEventListener("submit", handleLoginSubmit);
    }

    // Register Form
    const registerForm = document.getElementById("register-form");
    if (registerForm) {
        registerForm.addEventListener("submit", handleRegisterSubmit);
    }

    // Verify Form
    const verifyForm = document.getElementById("verify-form");
    if (verifyForm) {
        verifyForm.addEventListener("submit", handleVerifySubmit);
    }

    // Resend Code Button
    const resendBtn = document.getElementById("resend-code-btn");
    if (resendBtn) {
        resendBtn.addEventListener("click", handleResendCode);
    }

    // Switch View Links
    const toRegisterLink = document.getElementById("link-to-register");
    if (toRegisterLink) {
        toRegisterLink.addEventListener("click", (e) => {
            e.preventDefault();
            showView("register");
        });
    }

    const toLoginLink = document.getElementById("link-to-login");
    if (toLoginLink) {
        toLoginLink.addEventListener("click", (e) => {
            e.preventDefault();
            showView("login");
        });
    }
}

function setupDashboardNavListeners() {
    // Nav Header Links
    const navDash = document.getElementById("nav-link-dash");
    const navPlan = document.getElementById("nav-link-plan");
    const navTrips = document.getElementById("nav-link-trips");
    const navProfile = document.getElementById("nav-link-profile");
    const navLogout = document.getElementById("nav-link-logout");

    if (navDash) navDash.addEventListener("click", (e) => { e.preventDefault(); showView("dashboard"); });
    if (navPlan) navPlan.addEventListener("click", (e) => { e.preventDefault(); showView("planner"); });
    if (navTrips) navTrips.addEventListener("click", (e) => { e.preventDefault(); showView("trips"); });
    if (navProfile) navProfile.addEventListener("click", (e) => { e.preventDefault(); showView("profile"); });
    if (navLogout) navLogout.addEventListener("click", (e) => { e.preventDefault(); handleLogout(); });

    // Dashboard Cards Buttons
    const cardPlanBtn = document.getElementById("dash-card-plan-btn");
    const cardNavBtn = document.getElementById("dash-card-nav-btn");
    const cardTripsBtn = document.getElementById("dash-card-trips-btn");
    const cardProfileBtn = document.getElementById("dash-card-profile-btn");

    if (cardPlanBtn) cardPlanBtn.addEventListener("click", () => showView("planner"));
    if (cardNavBtn) cardNavBtn.addEventListener("click", () => showView("navigation"));
    if (cardTripsBtn) cardTripsBtn.addEventListener("click", () => showView("trips"));
    if (cardProfileBtn) cardProfileBtn.addEventListener("click", () => showView("profile"));
}

async function handleLoginSubmit(e) {
    e.preventDefault();
    hideAuthAlerts();

    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-password").value;

    if (!email || !password) {
        showAuthAlert("login", "Please enter both email and password.", "error");
        return;
    }

    const submitBtn = document.getElementById("login-submit-btn");
    const origText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Logging in...`;

    try {
        const response = await fetch("/api/auth/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            const msg = data.detail || "Incorrect email or password.";
            if (response.status === 403 || msg.includes("verify your email")) {
                unverifiedEmail = email;
                showView("verify");
                showAuthAlert("verify", "Please verify your email before logging in.", "warning");
            } else {
                showAuthAlert("login", msg, "error");
            }
            return;
        }

        // Login Success
        saveSession(data.token, data.user, true);
        updateNavbarUI(true);
        showView("dashboard");

    } catch (err) {
        console.error("Login submit error:", err);
        showAuthAlert("login", "Connection error. Please try logging in again.", "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = origText;
    }
}

async function handleRegisterSubmit(e) {
    e.preventDefault();
    hideAuthAlerts();

    const name = document.getElementById("reg-name").value.trim();
    const email = document.getElementById("reg-email").value.trim();
    const password = document.getElementById("reg-password").value;
    const confirmPassword = document.getElementById("reg-confirm-password").value;

    if (!name || !email || !password || !confirmPassword) {
        showAuthAlert("register", "Please fill in all required registration fields.", "error");
        return;
    }

    if (password !== confirmPassword) {
        showAuthAlert("register", "Password and confirm password do not match.", "error");
        return;
    }

    const submitBtn = document.getElementById("reg-submit-btn");
    const origText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Creating Account...`;

    try {
        const response = await fetch("/api/auth/register", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                name: name,
                email: email,
                password: password,
                confirm_password: confirmPassword
            })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            showAuthAlert("register", data.detail || "Registration failed. Please check your information.", "error");
            return;
        }

        // Registration Success -> Proceed to Verification View
        unverifiedEmail = email;
        showView("verify");
        showAuthAlert("verify", data.message || `We sent a 6-digit verification code to ${email}`, "success");
        startResendCooldown(45);


    } catch (err) {
        console.error("Register submit error:", err);
        showAuthAlert("register", "Connection error. Please try again.", "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = origText;
    }
}

async function handleVerifySubmit(e) {
    e.preventDefault();
    hideAuthAlerts();

    const code = document.getElementById("verify-code").value.trim();

    if (!code || code.length !== 6) {
        showAuthAlert("verify", "Please enter a valid 6-digit verification code.", "error");
        return;
    }

    const submitBtn = document.getElementById("verify-submit-btn");
    const origText = submitBtn.innerHTML;
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Verifying...`;

    try {
        const response = await fetch("/api/auth/verify-email", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                email: unverifiedEmail,
                code: code
            })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            showAuthAlert("verify", data.detail || "Incorrect verification code.", "error");
            return;
        }

        // Verification Success -> Redirect to Login with success banner
        showView("login");
        showAuthAlert("login", "Email verified successfully! You can now log in.", "success");

    } catch (err) {
        console.error("Verify submit error:", err);
        showAuthAlert("verify", "Connection error. Please try again.", "error");
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = origText;
    }
}

let resendTimer = null;

function startResendCooldown(seconds = 45) {
    const resendBtn = document.getElementById("resend-code-btn");
    if (!resendBtn) return;

    let remaining = seconds;
    resendBtn.disabled = true;
    resendBtn.innerHTML = `<i class="fa-solid fa-clock"></i> Resend Code (${remaining}s)`;

    if (resendTimer) clearInterval(resendTimer);

    resendTimer = setInterval(() => {
        remaining -= 1;
        if (remaining <= 0) {
            clearInterval(resendTimer);
            resendBtn.disabled = false;
            resendBtn.innerHTML = `<i class="fa-solid fa-rotate-right"></i> Resend Code`;
        } else {
            resendBtn.innerHTML = `<i class="fa-solid fa-clock"></i> Resend Code (${remaining}s)`;
        }
    }, 1000);
}

async function handleResendCode() {
    hideAuthAlerts();
    if (!unverifiedEmail) {
        showAuthAlert("verify", "Please enter your email on the login screen first.", "error");
        return;
    }

    const resendBtn = document.getElementById("resend-code-btn");
    resendBtn.disabled = true;
    resendBtn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Resending...`;

    try {
        const response = await fetch("/api/auth/resend-code", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email: unverifiedEmail })
        });

        const data = await response.json();

        if (!response.ok || !data.success) {
            const level = response.status === 429 ? "warning" : "error";
            showAuthAlert("verify", data.detail || "Failed to resend verification code.", level);
            resendBtn.disabled = false;
            resendBtn.innerHTML = `<i class="fa-solid fa-rotate-right"></i> Resend Code`;
            return;
        }

        showAuthAlert("verify", data.message || "Verification code sent successfully.", "success");
        startResendCooldown(45);

    } catch (err) {
        console.error("Resend code error:", err);
        showAuthAlert("verify", "Connection error. Please try again.", "error");
        resendBtn.disabled = false;
        resendBtn.innerHTML = `<i class="fa-solid fa-rotate-right"></i> Resend Code`;
    }
}


async function handleLogout() {
    if (currentToken) {
        try {
            await fetch("/api/auth/logout", {
                method: "POST",
                headers: { "Authorization": `Bearer ${currentToken}` }
            });
        } catch (e) {
            console.warn("Logout notice:", e);
        }
    }
    clearSession();
    showView("login");
    showAuthAlert("login", "You have been logged out successfully.", "info");
}

/* ==================================================
 * MY TRIPS & PROFILE DISPLAY LOGIC
 * ================================================== */
async function loadUserTripsHistory() {
    const listElem = document.getElementById("trips-history-list");
    if (!listElem) return;

    listElem.innerHTML = `<div class="loading-spinner"><i class="fa-solid fa-spinner fa-spin"></i> Loading your saved trips...</div>`;

    try {
        const response = await fetch("/api/trips", {
            headers: { "Authorization": `Bearer ${currentToken}` }
        });

        if (!response.ok) throw new Error("Failed to load trips history.");

        const data = await response.json();
        const trips = data.trips || [];

        if (trips.length === 0) {
            listElem.innerHTML = `
                <div class="empty-state-card">
                    <i class="fa-solid fa-map-location-dot empty-icon"></i>
                    <h3>No Saved Trips Yet</h3>
                    <p>Calculate routes and plan journeys to build your travel history.</p>
                    <button type="button" class="btn-primary" onclick="showView('planner')">
                        <i class="fa-solid fa-compass"></i> Plan a Journey
                    </button>
                </div>
            `;
            return;
        }

        let html = `<div class="trips-grid">`;
        trips.forEach(t => {
            const dateStr = new Date(t.created_at).toLocaleDateString("en-US", {
                year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'
            });
            html += `
                <div class="trip-card-item">
                    <div class="trip-card-header">
                        <span class="trip-date"><i class="fa-regular fa-calendar"></i> ${dateStr}</span>
                        <span class="mode-tag-badge">${t.travel_mode || 'CAR'}</span>
                    </div>
                    <div class="trip-route-title">
                        <strong>${t.source}</strong> <i class="fa-solid fa-arrow-right text-sky"></i> <strong>${t.destination}</strong>
                    </div>
                    <div class="trip-details-grid">
                        <div><span class="detail-label">Distance:</span> <strong>${t.distance_km} km</strong></div>
                        <div><span class="detail-label">Duration:</span> <strong>${t.estimated_duration}</strong></div>
                        <div><span class="detail-label">Traffic:</span> <strong>${t.traffic_condition}</strong></div>
                        <div><span class="detail-label">ETA:</span> <strong>${t.eta}</strong></div>
                    </div>
                </div>
            `;
        });
        html += `</div>`;
        listElem.innerHTML = html;

    } catch (err) {
        console.error("Load trips error:", err);
        listElem.innerHTML = `<div class="auth-alert error"><i class="fa-solid fa-circle-exclamation"></i> Unable to load your trips history. Please try again.</div>`;
    }
}

function loadUserProfileData() {
    if (!currentUser) return;
    const nameElem = document.getElementById("profile-name-val");
    const emailElem = document.getElementById("profile-email-val");
    const statusElem = document.getElementById("profile-status-val");

    if (nameElem) nameElem.textContent = currentUser.name || "N/A";
    if (emailElem) emailElem.textContent = currentUser.email || "N/A";
    if (statusElem) {
        statusElem.innerHTML = currentUser.is_verified ?
            `<span class="badge-verified"><i class="fa-solid fa-circle-check"></i> Verified</span>` :
            `<span class="badge-unverified"><i class="fa-solid fa-circle-xmark"></i> Unverified</span>`;
    }
}

async function saveCurrentTripToHistory(source, destination, distanceKm, durationText, trafficCondition, depTime, eta) {
    if (!currentUser || !currentToken) return;

    try {
        await fetch("/api/trips", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "Authorization": `Bearer ${currentToken}`
            },
            body: JSON.stringify({
                source: source,
                destination: destination,
                distance_km: distanceKm,
                travel_mode: currentTravelMode || "DRIVE",
                estimated_duration: durationText,
                traffic_condition: trafficCondition,
                departure_time: depTime,
                eta: eta
            })
        });
    } catch (e) {
        console.warn("Save trip history notice:", e);
    }
}

/* Helper alert functions */
function showAuthAlert(formType, msg, level = "error") {
    const alertElem = document.getElementById(`${formType}-alert`);
    if (alertElem) {
        const iconClass = level === "success" ? "fa-circle-check" : level === "warning" ? "fa-triangle-exclamation" : "fa-circle-exclamation";
        alertElem.innerHTML = `<i class="fa-solid ${iconClass}"></i> ${msg}`;
        alertElem.className = `auth-alert ${level}`;
        alertElem.style.display = "flex";
    }
}

function hideAuthAlerts() {
    const alerts = document.querySelectorAll(".auth-alert");
    alerts.forEach(a => {
        a.style.display = "none";
        a.innerHTML = "";
    });
}
