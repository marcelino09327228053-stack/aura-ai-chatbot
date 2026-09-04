# MB Future Tech AI Chatbot — Facebook Messenger Setup

MB Future Tech AI Chatbot can answer messages sent to a Facebook Page using the same company profile,
FAQ database, uploaded knowledge, conversation history, and selected AI provider
used by the web chat.

## 1. Configure MB Future Tech AI Chatbot

Add these values to `.env` (never commit real secrets):

```env
FACEBOOK_APP_ID=paste-the-meta-app-id-here
FACEBOOK_VERIFY_TOKEN=create-a-long-random-token-here
FACEBOOK_PAGE_ACCESS_TOKEN=paste-the-page-access-token-here
FACEBOOK_APP_SECRET=paste-the-meta-app-secret-here
FACEBOOK_COMPANY_ID=1
FACEBOOK_AI_PROVIDERS=gemini
FACEBOOK_LANGUAGE=filipino
FACEBOOK_GRAPH_API_VERSION=v23.0
FACEBOOK_OAUTH_REDIRECT_URI=https://your-domain.example/webhooks/facebook/oauth/callback
```

For the customer-friendly **Continue with Facebook** flow, configure
`FACEBOOK_APP_ID` and `FACEBOOK_APP_SECRET` once on the server. Customers can
then log in, choose a Page, and approve access without copying tokens.

- `FACEBOOK_VERIFY_TOKEN` is a private value you create. Enter the identical value
  in Meta's webhook setup.
- `FACEBOOK_PAGE_ACCESS_TOKEN` comes from the Messenger settings for the Page.
- `FACEBOOK_APP_SECRET` comes from Meta App Settings > Basic.
- `FACEBOOK_COMPANY_ID` selects the AI Chatbot company profile/database used for answers.
- `FACEBOOK_AI_PROVIDERS` accepts one or more comma-separated AI providers, such
  as `gemini` or `gemini,openai`.

Restart MB Future Tech AI Chatbot after changing `.env`.

## 2. Expose the local AI Chatbot for private testing

Start the webhook-only gateway on port 8001, then start a secure HTTPS tunnel to
port 8001. Do not expose the main AI Chatbot dashboard port. The public callback is:

```text
https://YOUR-TUNNEL-HOST/webhooks/facebook
```

The tunnel address is temporary unless a named/permanent tunnel is configured.

## 3. Configure the Meta app

1. Create or open a Meta Developer app and add Messenger.
2. Connect the Facebook Page.
3. Add the callback URL shown above.
4. Enter the exact `FACEBOOK_VERIFY_TOKEN` value.
5. Subscribe the Page to the `messages` and `messaging_postbacks` webhook fields.
6. Generate a Page Access Token and store it only in `.env`.
7. Copy the Meta App Secret to `.env`.

In development mode, test using accounts that have an app/Page role. Public users
may require the app to be Live and the required permissions to pass Meta review.

## Security behavior

- Every incoming POST must pass Meta's `X-Hub-Signature-256` verification.
- Access tokens and app secrets are never returned by the webhook.
- Duplicate webhook retries are ignored for one hour.
- Echo events are ignored to prevent reply loops.
- Long AI Chatbot replies are split below Messenger's text limit.
