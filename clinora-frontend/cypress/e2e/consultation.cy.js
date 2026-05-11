function disableAnimations() {
  cy.document().then((doc) => {
    const style = doc.createElement("style");
    style.innerHTML = `
      *, *::before, *::after {
        animation: none !important;
        transition: none !important;
        opacity: 1 !important;
        pointer-events: auto !important;
        transform: none !important;
      }
    `;
    doc.head.appendChild(style);
  });
}

describe("Consultation flow", () => {
  it("starts an intake session and sends a chat response", () => {
    cy.intercept("POST", "/api/session/start", {
      statusCode: 200,
      body: {
        session_id: "e2e-session",
        reply: "Thanks, I will ask a few focused questions.",
        safety: { final_risk: "low" },
        quick_replies: ["Yesterday", "Two days ago"],
      },
    }).as("startSession");

    cy.intercept("GET", "/api/sessions/e2e-session/uploads", {
      statusCode: 200,
      body: [],
    }).as("sessionUploads");

    cy.intercept("POST", "/api/session/chat/stream", {
      statusCode: 200,
      headers: { "content-type": "text/event-stream" },
      body: [
        'data: {"type":"interviewer_reply","text":"Do you also have shortness of breath?","trigger":false,"quick_replies":["Yes","No"]}',
        'data: {"type":"done"}',
        "",
      ].join("\n\n"),
    }).as("chatStream");

    cy.visit("/input");
    disableAnimations();

    cy.contains("button", "Try Example").click({ force: true });
    cy.get('input[type="checkbox"]').check({ force: true });
    cy.contains("button", /begin/i).click();

    cy.wait("@startSession").its("request.body").should("include", {
      bodyPart: "Chest",
      duration: "1–3 days",
      severity: 7,
      consent_to_provider_review: true,
    });
    cy.location("pathname").should("eq", "/chat");
    cy.contains("Thanks, I will ask a few focused questions.").should("exist");

    cy.get("input[placeholder]").last().type("The pain started yesterday");
    cy.contains("button", /send/i).click();

    cy.wait("@chatStream").its("request.body").should("deep.include", {
      session_id: "e2e-session",
      user_message: "The pain started yesterday",
    });
    cy.contains("The pain started yesterday").should("exist");
    cy.contains("Do you also have shortness of breath?").should("exist");
  });

  it("completes diagnosis and opens export links", () => {
    cy.intercept("POST", "/api/session/start", {
      statusCode: 200,
      body: {
        session_id: "e2e-diagnosis-session",
        reply: "Thanks, I will ask a few focused questions.",
        safety: { final_risk: "low" },
        quick_replies: [],
      },
    }).as("startSession");

    cy.intercept("GET", "/api/sessions/e2e-diagnosis-session/uploads", {
      statusCode: 200,
      body: [],
    });

    cy.intercept("POST", "/api/session/chat/stream", {
      statusCode: 200,
      headers: { "content-type": "text/event-stream" },
      body: [
        'data: {"type":"interviewer_reply","text":"I have enough information to prepare the diagnosis.","trigger":true}',
        'data: {"type":"done"}',
        "",
      ].join("\n\n"),
    }).as("chatStream");

    cy.intercept("POST", "/api/session/diagnose/stream", {
      statusCode: 200,
      headers: { "content-type": "text/event-stream" },
      body: [
        'data: {"type":"phase_sep","label":"DIAGNOSIS"}',
        'data: {"type":"diagnosis_ready","diagnosis":"Likely pleuritic chest pain. Consider pulmonary embolism as a differential diagnosis.","review":"Safety review recommends urgent assessment if symptoms worsen.","refs":[{"title":"Chest pain guideline","url":"https://example.com/ref"}],"cot":null}',
        'data: {"type":"done"}',
        "",
      ].join("\n\n"),
    }).as("diagnoseStream");

    cy.intercept("GET", "/api/session/e2e-diagnosis-session", {
      statusCode: 200,
      body: {
        messages: [
          { role: "user", content: "Chest pain after a flight" },
          { role: "ai", content: "I have enough information." },
        ],
      },
    });

    cy.intercept("GET", "/api/session/e2e-diagnosis-session/peer-review", {
      statusCode: 200,
      body: { available: false, reason: "mocked" },
    });

    cy.visit("/input");
    disableAnimations();

    cy.contains("button", "Try Example").click({ force: true });
    cy.get('input[type="checkbox"]').check({ force: true });
    cy.contains("button", /begin/i).click();
    cy.wait("@startSession");

    cy.get("input[placeholder]").last().type("The pain worsens when breathing");
    cy.contains("button", /send/i).click();

    cy.wait("@chatStream");
    cy.wait("@diagnoseStream");
    cy.location("pathname", { timeout: 8000 }).should("eq", "/result");
    cy.contains("Likely pleuritic chest pain").should("exist");

    cy.window().then((win) => {
      cy.stub(win, "open").as("windowOpen");
    });
    cy.contains("button", /pdf/i).click();
    cy.get("@windowOpen").should(
      "have.been.calledWith",
      "/api/session/e2e-diagnosis-session/export/pdf",
      "_blank",
    );

    cy.contains("button", /json/i).click();
    cy.get("@windowOpen").should(
      "have.been.calledWith",
      "/api/session/e2e-diagnosis-session/export/json",
      "_blank",
    );
  });
});
