# Conference Quote Search

A Flask web application for searching and retrieving quotes from the General Conference talks of The Church of Jesus Christ of Latter-day Saints (publicly avialbale, talks from April 2018 to October 2024) using semantic search and OpenAI embeddings.

## Features

- Semantic search using OpenAI embeddings and Pinecone vector database
- Real-time YouTube video integration with timestamp support
- Dark/light mode UI
- Quote downloading functionality
- Response caching for improved performance
- Asynchronous job processing

## Tech Stack

- Backend: Flask + Python
- Vector Search: Pinecone + OpenAI Embeddings
- Frontend: HTML/CSS/JavaScript
- Additional: An LLM of your choice for query processing

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure environment variables:
```env
OPENAI_API_KEY=your_openai_key
PINECONE_API_KEY=your_pinecone_key
```

3. Start the server:
```bash
python main.py
```

## Architecture

### Backend Components

- `main.py`: Flask application and route handlers
- `pinecone_utils_openai.py`: Vector search and embedding functionality
- `queue_utils.py`: Asynchronous job processing
- `openai_utils.py`: OpenAI API integration

### Frontend Components

- `index.html`: Main application interface
- `scripts.js`: Client-side functionality
- `styles.css`: Application styling

## API Endpoints

- `POST /query`: Submit a search query
- `GET /status/<job_id>`: Check job status
- `GET /`: Serve main application

## Development

The application uses a worker thread for processing queries asynchronously:

```python
def process_query(user_message):
    # Query OpenAI embeddings
    relevant_paragraphs = query_openai_paragraphs(query=user_message, top_k=10)
    
    # Process with GPT-4o
    response = get_chat_completion(
        system_prompt=search_assistant_system_prompt,
        user_prompt=user_prompt
    )
    
    # Verify and return results
    return verify_response(quotes, relevant_paragraphs)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Submit a pull request


## Contact Informaton
Should you have any questions, please contact Hwa Lee at https://github.com/leezorba
