# AI and audio developer defaults

The GM narration endpoint uses OpenRouter's chat completions API with
`openai/gpt-6-luna`. Its model ID lives in `Settings.openrouter_model` and may be
overridden with `VDM_OPENROUTER_MODEL`. The API key is loaded from
`VDM_OPENROUTER_API_KEY` in the process environment. Do not put a key in Git or
`vdm.yaml`; the loader rejects a key in YAML. The z1-hestia service starts via
`bwsx exec --secret VDM_OPENROUTER_API_KEY=OpenRouter`, which injects the secret
only into the service process.

The room host and GM roles can request narration after at least one chronicle
event. The server sends at most 12 recent events, clips each event to 600
characters, and requests at most 350 output tokens. A successful reply becomes
a normal narration event. No model call is made for players or spectators.

`typesafe/jev-1.13` is configured as `Settings.jev_model` for a future decision
step. Jev uses OpenRouter's **Decisions API**, not chat completions, and returns
typed choices and probabilities rather than prose. A useful first application
is classifying a submitted action as dialogue, exploration, combat, rules
question, or other. That classification can help a GM find actions needing a
rules check. It must remain advisory: room roles and mechanics stay enforced by
code or the GM. We should gather labeled actions from testing before choosing
a confidence threshold or enabling automatic routing.

OpenRouter references:

- [GPT Luna model](https://openrouter.ai/openai/gpt-6-luna)
- [Chat completions API](https://openrouter.ai/docs/api/api-reference/chat/send-chat-completion-request)
- [Jev model](https://openrouter.ai/typesafe/jev-1.13/api)
- [Jev Decisions API usage](https://openrouter.ai/blog/tutorials/jev-vs-llm-when-to-use-each/)

On z1-hestia, the CUDA `audio.cpp` container is running on host port 8880. Its
local health endpoint reports `backend=cuda` and two models. Set
`VDM_AUDIO_CPP_URL=http://127.0.0.1:8880` (the default). The authenticated
`/api/audio/health` endpoint confirms the VDM process can reach it. Its
OpenAI-compatible speech and transcription routes are `/v1/audio/speech` and
`/v1/audio/transcriptions`; streaming/browser voice flows are future work.
