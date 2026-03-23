// frappe_next_bridge — login page enhancements
// Runs on every web page; all logic is gated on .for-login presence.

(function () {
  if (!document.querySelector(".for-login")) return;

  // Replace default title with a friendlier greeting
  var heading = document.querySelector(".page-card-head h4");
  if (heading) {
    heading.textContent = "Hello, there!";
  }

  // Add subtitle below the heading if it doesn't already exist
  var head = document.querySelector(".page-card-head");
  if (head && !head.querySelector(".login-subtitle")) {
    var sub = document.createElement("p");
    sub.className = "login-subtitle";
    sub.textContent = "Log in to access your company workspace.";
    head.appendChild(sub);
  }
})();
