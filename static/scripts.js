let allQuotes = [];
let displayedCount = 5;

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

  submitQuery();
}

function setLoadingState(isLoading, elements) {
  if (elements.submitButton) elements.submitButton.disabled = isLoading;
  if (elements.loadingIndicator) {
    elements.loadingIndicator.style.display = isLoading ? "flex" : "none";
  }
  if (!isLoading) {
    // Ensure the spinner is completely hidden after the operation
    elements.loadingIndicator.style.opacity = 0;
  }
}

function submitQuery() {
  const input = document.querySelector("#question");
  const elements = {
    submitButton: document.getElementById("submitButton"),
    loadingIndicator: document.getElementById("loadingIndicator"),
    responseContainer: document.getElementById("responseContainer"),
  };

  // Input Validation
  if (!input.value.trim()) {
    alert("Please enter a valid question");
    setLoadingState(false, elements);
    return;
  }

  // Clear old results and show spinner
  elements.responseContainer.innerHTML = "";
  setLoadingState(true, elements);

  fetch("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question: input.value.trim() }),
  })
    .then((response) => response.json())
    .then((data) => {
      // If server returned an immediate error
      if (data.error) {
        throw new Error(data.error);
      }
      // If we got a job_id, poll the /status/<job_id> route
      if (data.job_id) {
        pollJobStatus(data.job_id, elements);
      }
      // Or if the server returned actual data directly (without queueing)
      else if (data.response_text) {
        displayResults(data.response_text);
        setLoadingState(false, elements);
      }
    })
    .catch((error) => {
      console.error("Error:", error.message);
      elements.responseContainer.innerHTML = `
        <p class="error">Error: ${error.message}. Please try again later.</p>`;
      setLoadingState(false, elements);
    });
}

function pollJobStatus(jobId, elements, retries = 60) {
  const pollingInterval = 2000; // 2 seconds

  const poll = () => {
    fetch(`/status/${jobId}`)
      .then((response) => {
        if (response.status === 404) {
          throw new Error("Job not found. Please try again.");
        }
        return response.json();
      })
      .then((data) => {
        if (data.status === "pending") {
          if (retries > 0) {
            // keep polling until we run out of retries
            setTimeout(() => {
              retries--;
              poll();
            }, pollingInterval);
          } else {
            throw new Error("The query took too long. Please try again.");
          }
        } else if (data.status === "complete") {
          if (data.response_text) {
            displayResults(data.response_text);
          }
          setLoadingState(false, elements);
        } else if (data.status === "error") {
          throw new Error(
            data.error || "An error occurred processing your request."
          );
        }
      })
      .catch((error) => {
        console.error("Polling error:", error);
        elements.responseContainer.innerHTML = `
          <p class="error">Error: ${error.message}. Please try again.</p>`;
        setLoadingState(false, elements);
      });
  };

  // Start polling immediately
  poll();
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
    .map((quote) => validateAndRenderQuote(quote))
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
            ? `<button onclick="replayQuote(${
                quote.index
              }, ${startTime})" class="secondary-button">
                Play Quote (${formatTime(startTime)})
              </button>`
            : ""
        }
      </div>
      ${videoId ? generateVideoEmbed(videoId, startTime) : ""}
    </div>
  `;
}

function generateVideoEmbed(videoId, startTime) {
  return `
    <div class="video-container">
      <iframe src="https://www.youtube.com/embed/${videoId}?start=${startTime}&enablejsapi=1"
              allowfullscreen></iframe>
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

// YouTube Integration
let players = {};

function initYouTubeAPI() {
  if (!window.YT) {
    const tag = document.createElement("script");
    tag.src = "https://www.youtube.com/iframe_api";
    document.head.appendChild(tag);
  } else {
    setupPlayers();
  }
}

function onYouTubeIframeAPIReady() {
  setupPlayers();
}

function setupPlayers() {
  document
    .querySelectorAll(".video-container iframe")
    .forEach((iframe, index) => {
      players[index] = new YT.Player(iframe.id);
    });
}

function replayQuote(index, startTime) {
  if (players[index]?.seekTo) {
    players[index].seekTo(startTime);
    players[index].playVideo();
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
