import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { expect, test, vi } from "vitest";
import { App } from "./App";

vi.stubGlobal("fetch", vi.fn(async () => ({ ok: true, json: async () => ({ items: [] }) })));

test("renders the editorial control room", async () => {
  render(<MemoryRouter><App /></MemoryRouter>);
  expect(await screen.findByText("今天的生产台")).toBeInTheDocument();
  expect(screen.getByText("最近 Runs")).toBeInTheDocument();
});
