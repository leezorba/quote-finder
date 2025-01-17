// scripts.js

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
async function handleSearch(event) {
  event.preventDefault();

  const elements = {
    submitButton: document.getElementById("submitButton"),
    loadingIndicator: document.getElementById("loadingIndicator"),
    responseContainer: document.getElementById("responseContainer"),
  };

  setLoadingState(true, elements);
  hideResults();

  try {
    const response = await submitQuery();
    handleSearchResponse(response);
  } catch (error) {
    showError(error);
  } finally {
    setLoadingState(false, elements);
  }
}

async function submitQuery() {
  const question = document.getElementById("question").value;

  // We always use "embed3" now, so let's hardcode it
  const selectedIndex = "embed3";

  const response = await fetch("/query", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, selectedIndex }),
  });

  // If the server returns 500 or 404, etc., handle it:
  if (!response.ok) {
    let errorData = {};
    try {
      errorData = await response.json();
    } catch (parseErr) {
      // fallback if the JSON is not parseable
      throw new Error(`HTTP ${response.status} error`);
    }
    throw new Error(errorData.error || `HTTP ${response.status} error`);
  }

  // If response.ok is true, parse JSON normally
  return response.json();
}

function showError(error) {
  // Display the error message to the user
  const container = document.getElementById("responseContainer");
  container.style.display = "block";
  container.innerHTML = `
    <div class="quote-card error">
      <p>${error.message}</p>
    </div>
  `;
}

function handleSearchResponse(response) {
  if (response.error) throw new Error(response.error);

  allQuotes = response.response_text;
  displayedCount = Math.min(5, allQuotes.length);

  if (allQuotes.length > 0) {
    renderQuotes();
    showActionButtons();
  } else {
    showNoResultsMessage();
  }
}

// UI State Management
function setLoadingState(isLoading, elements) {
  elements.submitButton.disabled = isLoading;
  elements.loadingIndicator.style.display = isLoading ? "flex" : "none";
}

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

// Quote Rendering
function renderQuotes() {
  const container = document.getElementById("responseContainer");
  container.innerHTML = allQuotes
    .slice(0, displayedCount)
    .map((quote, index) => {
      const videoId = getYouTubeVideoId(quote.youtube_link);
      const startTime = parseInt(quote.start_time) || 0;
      const endTime = parseInt(quote.end_time) || 0;
      return generateQuoteCard(quote, videoId, startTime, endTime, index);
    })
    .join("");

  container.style.display = "block";
  initYouTubeAPI();
}

function generateQuoteCard(quote, videoId, startTime, endTime, index) {
  const session = getSessionInfo(quote.paragraph_deep_link);
  const videoEmbed = videoId
    ? generateVideoEmbed(videoId, startTime, index)
    : "";

  return `
   <div class="quote-card">
     <div class="quote-header">
       <h3>${quote.speaker}</h3>
       <p>${quote.role}</p>
     </div>
     <div class="quote-metadata">
       <p><strong>Title:</strong> ${quote.title}</p>
       <p><strong>Session:</strong> ${session}</p>
     </div>
     <p class="quote-text">${quote.paragraph_text}</p>
     <div class="quote-actions">
       <button onclick="window.open('${quote.paragraph_deep_link}', '_blank')"
               class="secondary-button">Read in Context</button>
       ${
         videoId
           ? `
         <button onclick="replayQuote(${index}, ${startTime})"
                 class="secondary-button">Play Quote (${formatTime(
                   startTime
                 )})</button>
       `
           : ""
       }
     </div>
     ${videoEmbed}
   </div>
 `;
}

function generateVideoEmbed(videoId, startTime, index) {
  return `
   <div class="video-container">
     <iframe id="video-${index}"
             src="https://www.youtube.com/embed/${videoId}?start=${startTime}&enablejsapi=1"
             allowfullscreen>
     </iframe>
   </div>
 `;
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

// Download Functionality
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
           ? `
         <a href="https://youtube.com/watch?v=${videoId}&t=${startTime}s" 
            target="_blank">Watch on YouTube (${formatTime(startTime)})</a>
       `
           : ""
       }
     </div>
   </div>
 `;
}
