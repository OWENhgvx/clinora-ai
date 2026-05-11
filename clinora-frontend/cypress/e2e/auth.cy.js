describe("Auth entry flow", () => {
  it("lets users choose and change login roles", () => {
    cy.visit("/auth");
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

    cy.contains("Sign in as").should("be.visible");
    cy.contains("button", "Patient").click();

    cy.contains("PATIENT").should("be.visible");
    cy.get('input[placeholder="username"]').should("be.visible");

    cy.contains("button", "change").click();
    cy.contains("button", "Provider").click();

    cy.contains("PROVIDER").should("be.visible");
    cy.get('input[placeholder="username"]').should("be.visible");
  });
});
