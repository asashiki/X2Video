import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, test, vi } from "vitest";
import { App } from "./App";

vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => ({ items: [] }) })));

test("renders the editorial control room", async () => {
  window.localStorage.clear();
  render(<MemoryRouter><App /></MemoryRouter>);
  expect(await screen.findByText("今天的生产台")).toBeInTheDocument();
  expect(screen.getByText("最近 Runs")).toBeInTheDocument();
  await waitFor(() => expect(document.documentElement.dataset.theme).toBe("light"));
  fireEvent.click(screen.getByRole("button", { name: "切换到深色模式" }));
  await waitFor(() => expect(document.documentElement.dataset.theme).toBe("dark"));
});
