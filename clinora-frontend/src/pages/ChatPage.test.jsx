import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import ChatPage from "./ChatPage";

vi.mock("../components/CameraCapture", () => ({
  default: () => <button type="button">camera</button>,
}));

function makeResumeSession() {
  return {
    id: "session-123",
    symptoms: { description: "Chest discomfort for two days" },
    messages: [
      {
        role: "agent",
        agent_type: "interviewer",
        content: "What symptoms are you experiencing?",
        created_at: "2026-04-25T10:00:00Z",
      },
    ],
  };
}

function makeApi(overrides = {}) {
  return {
    sessionUploads: vi.fn().mockResolvedValue([]),
    chatStream: vi.fn().mockResolvedValue(undefined),
    diagnoseStream: vi.fn().mockResolvedValue(undefined),
    session: vi.fn().mockResolvedValue({ messages: [] }),
    uploadSessionFile: vi.fn(),
    ...overrides,
  };
}

describe("ChatPage", () => {
  it("sends a typed message to the active session", async () => {
    const api = makeApi();

    render(
      <ChatPage
        api={api}
        symptoms={{ description: "Chest discomfort" }}
        onComplete={vi.fn()}
        onBack={vi.fn()}
        resumeSession={makeResumeSession()}
      />,
    );

    const input = screen.getByPlaceholderText("chat.placeholder");
    fireEvent.change(input, { target: { value: "My pain started yesterday" } });
    fireEvent.click(screen.getByRole("button", { name: "chat.send" }));

    await waitFor(() => {
      expect(api.chatStream).toHaveBeenCalledWith(
        {
          session_id: "session-123",
          user_message: "My pain started yesterday",
          attachments: [],
        },
        expect.any(Function),
      );
    });
    expect(screen.getByText("My pain started yesterday")).toBeInTheDocument();
  });

  it("disables the composer while a message is sending", async () => {
    let resolveChat;
    const api = makeApi({
      chatStream: vi.fn(
        () =>
          new Promise((resolve) => {
            resolveChat = resolve;
          }),
      ),
    });

    render(
      <ChatPage
        api={api}
        symptoms={{ description: "Chest discomfort" }}
        onComplete={vi.fn()}
        onBack={vi.fn()}
        resumeSession={makeResumeSession()}
      />,
    );

    const input = screen.getByPlaceholderText("chat.placeholder");
    const sendButton = screen.getByRole("button", { name: "chat.send" });

    fireEvent.change(input, { target: { value: "It feels sharp" } });
    fireEvent.click(sendButton);

    await waitFor(() => {
      expect(input).toBeDisabled();
      expect(sendButton).toBeDisabled();
    });

    resolveChat();
  });

  it("shows a log entry when chat streaming fails", async () => {
    const api = makeApi({
      chatStream: vi.fn().mockRejectedValue(new Error("Network down")),
    });

    render(
      <ChatPage
        api={api}
        symptoms={{ description: "Chest discomfort" }}
        onComplete={vi.fn()}
        onBack={vi.fn()}
        resumeSession={makeResumeSession()}
      />,
    );

    fireEvent.change(screen.getByPlaceholderText("chat.placeholder"), {
      target: { value: "I feel dizzy" },
    });
    fireEvent.click(screen.getByRole("button", { name: "chat.send" }));

    expect(await screen.findByText("Error: Network down")).toBeInTheDocument();
  });
});
