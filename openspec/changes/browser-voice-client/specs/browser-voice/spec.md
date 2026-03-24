## ADDED Requirements

### Requirement: Browser voice widget
The system SHALL serve an HTML page with a voice call button that connects to the AI agent via Twilio Client SDK.

#### Scenario: User clicks call button
- **WHEN** a user clicks the call button on the voice widget page
- **THEN** the browser SHALL request microphone permission, fetch a token, and establish a voice call to the agent

#### Scenario: Call in progress
- **WHEN** a browser call is active
- **THEN** the widget SHALL show "Beszélgetés folyamatban..." status and a hangup button

#### Scenario: Call ends
- **WHEN** the agent says farewell or the user clicks hangup
- **THEN** the call SHALL disconnect and the widget SHALL return to idle state

### Requirement: Mobile browser support
The widget SHALL work on mobile browsers (Chrome, Safari) with microphone access.

#### Scenario: Mobile user
- **WHEN** a user opens the widget on a mobile phone browser
- **THEN** the call button and microphone SHALL work the same as desktop

### Requirement: Handle browser caller identity
The webhook SHALL handle `client:*` caller identities from browser calls by looking up the identity name in contacts or using default context.

#### Scenario: Browser call with identity
- **WHEN** a browser call arrives with `From: client:gabor`
- **THEN** the system SHALL look up "gabor" in contacts and use the matching customer data

#### Scenario: Browser call without identity
- **WHEN** a browser call arrives with `From: client:anonymous`
- **THEN** the system SHALL use default context and greet generically
