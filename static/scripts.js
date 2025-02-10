let allQuotes = [];
let displayedCount = 5;

// 1) Store references to YT players by index
let players = {};

// Utility Functions
function getYouTubeVideoId(url) {
  if (!url) return null;
  const regExp = /^.*(?:youtu.be\/|v\/|e\/|u\/\\w+\/|embed\/|v=)([^#\&\?]*).*/;
  const match = url.match(regExp);
  return match && match[1];
}

function formatTime(seconds) {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

function getSessionInfo(deepLink) {
  const match = deepLink.match(/\/(\d{4})\/(\d{2})\//);
  if (!match) return "";
  return `${match[2] === "04" ? "April" : "October"} ${match[1]}`;
}

// Event Listeners Setup
document.addEventListener("DOMContentLoaded", () => {
  // 1) Define possible placeholder strings
  const placeholders = [
    "How can I find more peace in my life?",
    "I have a friend going through .... what quotes would be good for her?",
    "What can I do to better understand ...?",
  ];

  // 2) Pick one at random
  const randomPlaceholder =
    placeholders[Math.floor(Math.random() * placeholders.length)];

  // 3) Assign it to the #question input
  const questionInput = document.getElementById("question");
  if (questionInput) {
    questionInput.placeholder = randomPlaceholder;
  }

  setupEventListeners();
  hideActionButtons();
});

function setupEventListeners() {
  setupDarkMode();
  setupSearchForm();
  setupActionButtons();
}

function setupDarkMode() {
  document.getElementById("toggleDarkMode").addEventListener("click", () => {
    document.body.classList.toggle("dark-mode");
    updateDarkModeButton();
  });
}

function updateDarkModeButton() {
  const isDark = document.body.classList.contains("dark-mode");
  document.getElementById("toggleDarkMode").textContent = isDark
    ? "Switch to Light Mode"
    : "Switch to Dark Mode";
}

document.getElementById("logoutButton").addEventListener("click", () => {
  window.location.href = "/logout"; // Assumes you have a /logout route
});

function setupSearchForm() {
  document
    .getElementById("searchForm")
    .addEventListener("submit", handleSearch);
}

function setupActionButtons() {
  document.getElementById("loadMoreButton").addEventListener("click", () => {
    displayedCount = allQuotes.length;
    renderQuotes();
    hideLoadMoreButton();
  });

  document.getElementById("downloadButton").addEventListener("click", () => {
    downloadResults(allQuotes.slice(0, displayedCount));
  });
}

// Search Handling
function handleSearch(event) {
  event.preventDefault();

  const elements = {
    submitButton: document.getElementById("submitButton"),
    loadingIndicator: document.getElementById("loadingIndicator"),
    responseContainer: document.getElementById("responseContainer"),
  };

  if (
    !elements.submitButton ||
    !elements.loadingIndicator ||
    !elements.responseContainer
  ) {
    console.error("One or more elements are missing:", elements);
    return;
  }

  setLoadingState(true, elements);
  hideResults();

  // Get and validate input
  const input = document.querySelector("#question");
  const query = input.value.trim();

  if (!query) {
    alert("Please enter a question");
    setLoadingState(false, elements);
    return;
  }

  // Submit query without clearing the input field
  submitQuery(query);
}

function setLoadingState(isLoading, elements) {
  if (elements.submitButton) elements.submitButton.disabled = isLoading;
  if (elements.loadingIndicator) {
    elements.loadingIndicator.style.display = isLoading ? "flex" : "none";
  }
}

function submitQuery(query) {
  const loadingSpinner = document.querySelector("#loading-spinner");
  const resultsContainer = document.querySelector("#responseContainer");

  loadingSpinner.style.display = "block";
  resultsContainer.innerHTML = "";

  fetch("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: query }),
  })
    .then((response) => response.json())
    .then((data) => {
      if (data.error) throw new Error(data.error);
      if (data.job_id) {
        pollJobStatus(data.job_id);
      } else if (data.response_text) {
        displayResults(data.response_text);
      }
    })
    .catch((error) => {
      loadingSpinner.style.display = "none";
      resultsContainer.innerHTML = `<p class="error">Error: ${error.message}</p>`;
    });
}

function pollJobStatus(jobId, retries = 30) {
  const pollingInterval = 2000; // 2 seconds
  const loadingSpinner = document.querySelector("#loading-spinner");
  const resultsContainer = document.querySelector("#responseContainer");

  if (!document.querySelector("#progress-message")) {
    resultsContainer.innerHTML =
      '<p id="progress-message">Processing query...</p>';
  }

  fetch(`/status/${jobId}`)
    .then((response) => response.json())
    .then((data) => {
      if (data.status === "pending") {
        document.querySelector("#progress-message").textContent =
          "Searching through conference talks...";
        if (retries > 0) {
          setTimeout(() => pollJobStatus(jobId, retries - 1), pollingInterval);
        } else {
          throw new Error("The query took too long. Please try again later.");
        }
      } else if (data.status === "complete") {
        loadingSpinner.style.display = "none";
        document.querySelector("#progress-message").remove();
        displayResults(data.response_text);
      } else if (data.status === "error") {
        loadingSpinner.style.display = "none";
        throw new Error(data.error);
      }
    })
    .catch((error) => {
      loadingSpinner.style.display = "none";
      resultsContainer.innerHTML = `<p class="error">Error: ${error.message}</p>`;
    });
}

// Display Search Results
function displayResults(responseText) {
  try {
    // Parse responseText into allQuotes
    if (typeof responseText === "string") {
      allQuotes = JSON.parse(responseText);
    } else {
      allQuotes = responseText;
    }

    displayedCount = Math.min(5, allQuotes.length);

    // Hide loadingIndicator once results are available
    document.getElementById("loadingIndicator").style.display = "none";

    // Render quotes or show "No Results"
    if (allQuotes.length > 0) {
      renderQuotes();
      showActionButtons();
      // Re-initialize YT players after rendering new quotes
      setupPlayers();
    } else {
      showNoResultsMessage();
    }
  } catch (error) {
    console.error("Error parsing or displaying results:", error);
    showError("Unable to display results. Please try again.");
  }
}

// Quote Rendering
function renderQuotes() {
  const container = document.getElementById("responseContainer");
  container.innerHTML = allQuotes
    .slice(0, displayedCount)
    // Assign an index to each quote for the YT Player logic
    .map((quote, i) => {
      quote.index = i;
      return validateAndRenderQuote(quote);
    })
    .join("");

  container.style.display = "block";
}

function validateAndRenderQuote(quote) {
  if (
    !quote.speaker ||
    !quote.paragraph_text ||
    !quote.paragraph_deep_link ||
    !quote.title
  ) {
    console.error("Invalid quote data", quote);
    return `<div class="error">Invalid quote data</div>`;
  }
  return generateQuoteCard(quote);
}

function generateQuoteCard(quote) {
  const videoId = getYouTubeVideoId(quote.youtube_link);
  const startTime = parseInt(quote.start_time) || 0;
  const session = getSessionInfo(quote.paragraph_deep_link);

  return `
    <div class="quote-card">
      <div class="quote-header">
        <h3>${quote.speaker}</h3>
        <p>${quote.role || ""}</p>
      </div>
      <div class="quote-metadata">
        <p><strong>Title:</strong> ${quote.title}</p>
        <p><strong>Session:</strong> ${session}</p>
      </div>
      <p class="quote-text">${quote.paragraph_text}</p>
      <div class="quote-actions">
        <button onclick="window.open('${
          quote.paragraph_deep_link
        }', '_blank')" class="secondary-button">
          Read in Context
        </button>
        ${
          videoId
            ? `<button onclick="replayQuote(${quote.index}, ${startTime})"
                       class="secondary-button">
                 Play Quote (${formatTime(startTime)})
               </button>`
            : ""
        }
      </div>
      ${videoId ? generateVideoEmbed(videoId, quote.index) : ""}
    </div>
  `;
}

// 2) Give each iframe a unique ID using the index
function generateVideoEmbed(videoId, index) {
  return `
    <div class="video-container">
      <iframe
        id="player-${index}"
        src="https://www.youtube.com/embed/${videoId}?enablejsapi=1"
        allowfullscreen
      ></iframe>
    </div>
  `;
}

function showNoResultsMessage() {
  const container = document.getElementById("responseContainer");
  container.innerHTML = `<p>No quotes found for the given query.</p>`;
  container.style.display = "block";
}

// Error Handling
function showError(error) {
  const container = document.getElementById("responseContainer");
  container.style.display = "block";
  container.innerHTML = `<p class="error">${error}</p>`;
}

// UI State Management
function hideResults() {
  document.getElementById("responseContainer").style.display = "none";
  hideActionButtons();
}

function hideActionButtons() {
  document.querySelector(".results-actions").style.display = "none";
  document.getElementById("loadMoreButton").style.display = "none";
}

function showActionButtons() {
  document.querySelector(".results-actions").style.display = "flex";
  document.getElementById("loadMoreButton").style.display =
    allQuotes.length > 5 ? "block" : "none";
}

function hideLoadMoreButton() {
  document.getElementById("loadMoreButton").style.display = "none";
}

// 3) YT IFrame Player setup
//    Called automatically by the YT script once it is ready.
function onYouTubeIframeAPIReady() {
  setupPlayers();
}

// Create a YT.Player for every rendered iframe
function setupPlayers() {
  const iframes = document.querySelectorAll(".video-container iframe");
  iframes.forEach((iframe, i) => {
    // The iframe has id="player-<index>" from generateVideoEmbed
    const iframeId = iframe.id;
    // If there's already a player, skip or destroy before re-creating
    if (players[i]) {
      // Optional: players[i].destroy();
    }
    players[i] = new YT.Player(iframeId, {
      // playerVars if you want to configure autoplay, etc.
      events: {
        // onReady: (event) => { event.target.playVideo(); },
      },
    });
  });
}

// 4) Seek to the correct time and play
function replayQuote(index, startTime) {
  const player = players[index];
  if (player && typeof player.seekTo === "function") {
    player.seekTo(startTime, true);
    player.playVideo();
  }
}

// Download Results
function downloadResults(quotes) {
  const html = generateDownloadHTML(quotes);
  const blob = new Blob([html], { type: "text/html" });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = "conference_quotes.html";
  link.click();

  URL.revokeObjectURL(url);
}

function generateDownloadHTML(quotes) {
  return `
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8">
        <title>Conference Quotes</title>
        <style>
          body {
            font-family: system-ui, sans-serif;
            line-height: 1.5;
            max-width: 800px;
            margin: 2rem auto;
            padding: 0 1rem;
          }
          .quote {
            margin-bottom: 2rem;
            padding: 1rem;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
          }
          .metadata { color: #64748b; }
          .links {
            margin-top: 1rem;
            display: flex;
            gap: 1rem;
          }
          .links a {
            color: #2563eb;
            text-decoration: none;
          }
          .links a:hover { text-decoration: underline; }
        </style>
      </head>
      <body>
        <h1>Conference Quotes</h1>
        ${quotes.map((quote) => generateDownloadQuoteHTML(quote)).join("")}
      </body>
    </html>
  `;
}

function generateDownloadQuoteHTML(quote) {
  const videoId = getYouTubeVideoId(quote.youtube_link);
  const startTime = parseInt(quote.start_time) || 0;
  const session = getSessionInfo(quote.paragraph_deep_link);

  return `
    <div class="quote">
      <h2>${quote.speaker}</h2>
      <div class="metadata">
        <p>${quote.role}</p>
        <p><strong>Title:</strong> ${quote.title}</p>
        <p><strong>Session:</strong> ${session}</p>
      </div>
      <p>${quote.paragraph_text}</p>
      <div class="links">
        <a href="${
          quote.paragraph_deep_link
        }" target="_blank">Read in Context</a>
        ${
          videoId
            ? `<a href="https://youtube.com/watch?v=${videoId}&t=${startTime}s" target="_blank">
                Watch on YouTube (${formatTime(startTime)})
              </a>`
            : ""
        }
      </div>
    </div>
  `;
}
