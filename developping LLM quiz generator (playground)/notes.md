## Structured output possible in:
                                                Input	    Cached input	Output
gpt-4.5-preview-2025-02-27 and later            $75.00      $37.50          $150.00
o3-mini-2025-1-31 and later                     $1.10       $0.55           $4.40
o1-2024-12-17 and later                         $15.00      $7.50           $60.00
gpt-4o-mini-2024-07-18 and later                $0.15       $0.075          $0.60
gpt-4o-2024-08-06 and later                     $2.50       $1.25           $10.00

select: gpt-4o-mini	

## Function calling has two primary use cases:

1. Fetching Data	
Retrieve up-to-date information to incorporate into the model's response (RAG). Useful for searching knowledge bases and retrieving specific data from APIs (e.g. current weather data).

2. Taking Action	
Perform actions like submitting a form, calling APIs, modifying application state (UI/frontend or backend), or taking agentic workflow actions (like handing off the conversation).

https://platform.openai.com/docs/guides/function-calling?api-mode=chat 

## Web search
Allow models to search the web for the latest information before generating a response.
Using the Chat Completions API, you can directly access the fine-tuned models and tool used by Search in ChatGPT.

When using Chat Completions, the model always retrieves information from the web before responding to your query. To use web_search_preview as a tool that models like gpt-4o and gpt-4o-mini invoke only when necessary, switch to using the Responses API.

Currently, you need to use one of these models to use web search in Chat Completions:

gpt-4o-search-preview
gpt-4o-mini-search-preview

## Tactics:

- Include details in your query to get more relevant answers
- Ask the model to adopt a persona
- Use delimiters to clearly indicate distinct parts of the input
- Specify the steps required to complete a task
- Provide examples
- Specify the desired length of the output

## Best practices for naming functions

- response or completion: entire API response
- reply or answer: only text answer
- parsed_response, model_output, structured: structured model by instructor
- raw_response, raw_output: JSON for debugging
