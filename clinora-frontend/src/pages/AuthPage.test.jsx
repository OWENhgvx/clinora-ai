import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import AuthPage from "./AuthPage";

vi.mock("gsap", () => ({
  gsap: {
    set: vi.fn(),
    to: vi.fn(),
    fromTo: vi.fn(),
    timeline: () => ({ to: vi.fn().mockReturnThis() }),
  },
}));

vi.mock("./auth/useAuthStarfield", () => ({
  useAuthStarfield: vi.fn(),
}));

vi.mock("./auth/useAuthGsapIdle", () => ({
  useAuthGsapIdle: vi.fn(),
}));

vi.mock("./auth/authAudioHue", () => ({
  nextHue: () => 35,
  playClick: vi.fn(),
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
});
