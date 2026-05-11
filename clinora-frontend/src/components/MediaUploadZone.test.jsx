import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import MediaUploadZone, { MAX_UPLOAD_BYTES } from "./MediaUploadZone";

describe("MediaUploadZone", () => {
  it("analyses selected files and reports completed items", async () => {
    const api = {
      analyzeFile: vi.fn().mockResolvedValue({
        analysis: "Patient note analysis",
        analysis_preview: "Patient note analysis",
        annotations: [],
      }),
      analyzeCompare: vi.fn(),
      analyzeOcr: vi.fn(),
    };
    const onUpdate = vi.fn();

    const { container } = render(
      <MediaUploadZone api={api} onUpdate={onUpdate} disabled={false} />,
    );

    expect(screen.getByText("upload.drop_title")).toBeInTheDocument();

    const input = container.querySelector('input[type="file"]');
    const file = new File(["clinical note"], "note.txt", {
      type: "text/plain",
    });

    fireEvent.change(input, { target: { files: [file] } });

    await waitFor(() => {
      expect(api.analyzeFile).toHaveBeenCalledWith(file, "en-US");
      expect(screen.getByText("note.txt")).toBeInTheDocument();
      expect(screen.getByText(/TXT/)).toBeInTheDocument();
    });

    await waitFor(() => {
      expect(onUpdate).toHaveBeenLastCalledWith(
        ["Patient note analysis"],
        expect.arrayContaining([
          expect.objectContaining({
            fileName: "note.txt",
            fileType: "txt",
            analysing: false,
            analysis: "Patient note analysis",
          }),
        ]),
      );
    });
  });

  it("rejects unsupported file types before analysis", async () => {
    const api = {
      analyzeFile: vi.fn(),
      analyzeCompare: vi.fn(),
      analyzeOcr: vi.fn(),
    };

    const { container } = render(
      <MediaUploadZone api={api} onUpdate={vi.fn()} disabled={false} />,
    );

    const input = container.querySelector('input[type="file"]');
    const file = new File(["binary"], "malware.exe", {
      type: "application/octet-stream",
    });

    fireEvent.change(input, { target: { files: [file] } });

    expect(api.analyzeFile).not.toHaveBeenCalled();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Unsupported file type: malware.exe",
    );
  });

  it("rejects files larger than the upload limit before analysis", async () => {
    const api = {
      analyzeFile: vi.fn(),
      analyzeCompare: vi.fn(),
      analyzeOcr: vi.fn(),
    };

    const { container } = render(
      <MediaUploadZone api={api} onUpdate={vi.fn()} disabled={false} />,
    );

    const input = container.querySelector('input[type="file"]');
    const file = new File(["clinical note"], "large-note.txt", {
      type: "text/plain",
    });
    Object.defineProperty(file, "size", {
      value: MAX_UPLOAD_BYTES + 1,
    });

    fireEvent.change(input, { target: { files: [file] } });

    expect(api.analyzeFile).not.toHaveBeenCalled();
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "File too large: large-note.txt (max 25 MB)",
    );
  });
});
