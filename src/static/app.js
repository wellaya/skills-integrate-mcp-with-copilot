document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const loginForm = document.getElementById("login-form");
  const logoutButton = document.getElementById("logout-button");
  const activityForm = document.getElementById("activity-form");
  const messageDiv = document.getElementById("message");
  const userStatus = document.getElementById("user-status");
  const authContainer = document.getElementById("auth-container");
  const adminContainer = document.getElementById("admin-container");
  let currentUser = null;

  function showMessage(message, type = "success") {
    messageDiv.textContent = message;
    messageDiv.className = type;
    messageDiv.classList.remove("hidden");
  }

  function updateAuthUI() {
    const signedIn = Boolean(currentUser);
    userStatus.textContent = signedIn
      ? `${currentUser.email} (${currentUser.role})`
      : "Not signed in";
    loginForm.classList.toggle("hidden", signedIn);
    logoutButton.classList.toggle("hidden", !signedIn);
    signupForm.classList.toggle("hidden", !signedIn);
    adminContainer.classList.toggle(
      "hidden",
      !signedIn || currentUser.role !== "teacher"
    );
    document.getElementById("email").value = signedIn && currentUser.role === "student"
      ? currentUser.email
      : "";
    document.getElementById("email").readOnly = signedIn && currentUser.role === "student";
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();
      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";
        const spotsLeft = details.max_participants - details.participants.length;
        const canUnregister = currentUser &&
          (currentUser.role === "teacher" || details.participants.includes(currentUser.email));
        const participantsHTML = details.participants.length > 0
          ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants.map((email) => `
                  <li><span class="participant-email">${email}</span>
                    ${canUnregister && (currentUser.role === "teacher" || email === currentUser.email)
                      ? `<button class="delete-btn" data-activity="${name}" data-email="${email}" aria-label="Unregister ${email}">Remove</button>`
                      : ""}
                  </li>`).join("")}
              </ul>
            </div>`
          : "<p><em>No participants yet</em></p>";

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">${participantsHTML}</div>`;
        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML = "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.target;
    const response = await fetch(`/activities/${encodeURIComponent(button.dataset.activity)}/unregister?email=${encodeURIComponent(button.dataset.email)}`, { method: "DELETE" });
    const result = await response.json();
    showMessage(result.message || result.detail, response.ok ? "success" : "error");
    if (response.ok) fetchActivities();
  }

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const response = await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        email: document.getElementById("login-email").value,
        password: document.getElementById("login-password").value,
      }),
    });
    const result = await response.json();
    if (!response.ok) return showMessage(result.detail, "error");
    currentUser = result;
    loginForm.reset();
    updateAuthUI();
    fetchActivities();
  });

  logoutButton.addEventListener("click", async () => {
    await fetch("/auth/logout", { method: "POST" });
    currentUser = null;
    updateAuthUI();
    fetchActivities();
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;
    const response = await fetch(`/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(email)}`, { method: "POST" });
    const result = await response.json();
    showMessage(result.message || result.detail, response.ok ? "success" : "error");
    if (response.ok) fetchActivities();
  });

  activityForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const response = await fetch("/activities", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        name: document.getElementById("activity-name").value,
        description: document.getElementById("activity-description").value,
        schedule: document.getElementById("activity-schedule").value,
        max_participants: Number(document.getElementById("activity-capacity").value),
      }),
    });
    const result = await response.json();
    showMessage(response.ok ? "Activity created" : result.detail, response.ok ? "success" : "error");
    if (response.ok) {
      activityForm.reset();
      fetchActivities();
    }
  });

  fetch("/auth/me")
    .then((response) => response.ok ? response.json() : null)
    .then((user) => {
      currentUser = user;
      updateAuthUI();
      fetchActivities();
    });
});
