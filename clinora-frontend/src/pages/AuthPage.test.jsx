import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import AuthPage from "./AuthPage";

vi.mock("./auth/useAuthStarfield", () => ({
  useAuthStarfield: vi.fn(),
}));

describe("AuthPage", () => {
  it("switches from role selection to provider login form", () => {
    render(
      <AuthPage
        api={{ loginJson: vi.fn(), register: vi.fn() }}
        onLogin={vi.fn()}
        onSkip={vi.fn()}
      />,
    );

    expect(screen.getByText("Sign in as")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /provider/i }));

    expect(screen.getByText(/PROVIDER/)).toBeInTheDocument();
    expect(screen.getByText("Sign In")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("username")).toBeInTheDocument();
  });

  it("shows a toast when login fails", async () => {
    const api = {
      loginJson: vi.fn().mockRejectedValue(new Error("Invalid credentials")),
      register: vi.fn(),
    };

    render(<AuthPage api={api} onLogin={vi.fn()} onSkip={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /patient/i }));
    fireEvent.change(screen.getByPlaceholderText("username"), {
      target: { value: "alice" },
    });
    fireEvent.change(screen.getByPlaceholderText("••••••••"), {
      target: { value: "wrong-password" },
    });
    fireEvent.click(screen.getByText("Sign In →"));

    await waitFor(() => {
      expect(api.loginJson).toHaveBeenCalledWith({
        username: "alice",
        password: "wrong-password",
      });
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Invalid credentials",
      );
    });
  });

  it("submits the expanded patient registration profile", async () => {
    const api = {
      loginJson: vi.fn(),
      register: vi.fn().mockResolvedValue({
        token: "token-123",
        user: { username: "alice", role: "patient" },
      }),
    };

    render(<AuthPage api={api} onLogin={vi.fn()} onSkip={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /patient/i }));
    fireEvent.click(screen.getByRole("button", { name: /register/i }));
    fireEvent.change(screen.getByPlaceholderText("Your name"), {
      target: { value: "Alice Patient" },
    });
    fireEvent.change(screen.getByPlaceholderText("username"), {
      target: { value: "alice" },
    });
    fireEvent.change(screen.getByPlaceholderText("you@example.com"), {
      target: { value: "alice@example.com" },
    });
    fireEvent.change(screen.getAllByPlaceholderText("••••••••")[0], {
      target: { value: "securepass123" },
    });
    fireEvent.change(screen.getAllByPlaceholderText("••••••••")[1], {
      target: { value: "securepass123" },
    });
    fireEvent.change(screen.getByLabelText("Birth Date"), {
      target: { value: "1990-01-01" },
    });
    fireEvent.change(screen.getByLabelText("Sex"), {
      target: { value: "female" },
    });
    fireEvent.change(screen.getByPlaceholderText("170"), {
      target: { value: "170" },
    });
    fireEvent.change(screen.getByPlaceholderText("65"), {
      target: { value: "65" },
    });
    fireEvent.change(screen.getByPlaceholderText("e.g. hypertension"), {
      target: { value: "migraine" },
    });
    fireEvent.click(screen.getByRole("button", { name: "Add" }));
    fireEvent.click(screen.getByLabelText(/I agree to the Data Authorization Agreement/i));
    fireEvent.click(screen.getByText("Create Account →"));

    await waitFor(() => {
      expect(api.register).toHaveBeenCalledWith(
        expect.objectContaining({
          username: "alice",
          email: "alice@example.com",
          height_cm: 170,
          weight_kg: 65,
          chronic_conditions: ["migraine"],
          data_authorization_accepted: true,
        }),
      );
      expect(api.register.mock.calls[0][0]).not.toHaveProperty("age");
      expect(api.register.mock.calls[0][0]).not.toHaveProperty("verification_code");
      expect(api.register.mock.calls[0][0]).not.toHaveProperty("chronic_condition_draft");
    });
  });

  it("omits patient health fields from provider registration", async () => {
    const api = {
      loginJson: vi.fn(),
      register: vi.fn().mockResolvedValue({
        token: "provider-token",
        user: { username: "doctor", role: "provider" },
      }),
    };

    render(<AuthPage api={api} onLogin={vi.fn()} onSkip={vi.fn()} />);

    fireEvent.click(screen.getByRole("button", { name: /provider/i }));
    fireEvent.click(screen.getByRole("button", { name: /register/i }));

    expect(screen.queryByLabelText("Height cm")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Weight kg")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Allergies")).not.toBeInTheDocument();
    expect(screen.queryByLabelText("Chronic Conditions")).not.toBeInTheDocument();

    fireEvent.change(screen.getByPlaceholderText("Dr. Jane Smith"), {
      target: { value: "Dr. Jane Smith" },
    });
    fireEvent.change(screen.getByPlaceholderText("username"), {
      target: { value: "doctor" },
    });
    fireEvent.change(screen.getByPlaceholderText("you@example.com"), {
      target: { value: "doctor@example.com" },
    });
    fireEvent.change(screen.getAllByPlaceholderText("••••••••")[0], {
      target: { value: "securepass123" },
    });
    fireEvent.change(screen.getAllByPlaceholderText("••••••••")[1], {
      target: { value: "securepass123" },
    });
    fireEvent.change(screen.getByLabelText("Birth Date"), {
      target: { value: "1980-01-01" },
    });
    fireEvent.change(screen.getByLabelText("Sex"), {
      target: { value: "female" },
    });
    fireEvent.change(screen.getByLabelText("License Number"), {
      target: { value: "LIC-123" },
    });
    fireEvent.change(screen.getByLabelText("Hospital"), {
      target: { value: "Clinora General Hospital" },
    });
    fireEvent.change(screen.getByLabelText("Department"), {
      target: { value: "Internal Medicine" },
    });
    fireEvent.change(screen.getByPlaceholderText("Internal medicine, surgery..."), {
      target: { value: "Cardiology" },
    });
    fireEvent.change(screen.getByLabelText("Years"), {
      target: { value: "8" },
    });
    fireEvent.change(screen.getByPlaceholderText("Attending physician"), {
      target: { value: "Attending Physician" },
    });
    fireEvent.change(screen.getByPlaceholderText("File name or verification URL"), {
      target: { value: "credential.pdf" },
    });
    fireEvent.click(screen.getByText("Create Account →"));

    await waitFor(() => {
      const payload = api.register.mock.calls[0][0];
      expect(payload.role).toBe("provider");
      expect(payload).not.toHaveProperty("height_cm");
      expect(payload).not.toHaveProperty("weight_kg");
      expect(payload).not.toHaveProperty("allergies");
      expect(payload).not.toHaveProperty("chronic_conditions");
    });
  });
});
