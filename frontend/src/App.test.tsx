import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import App from "./App";

test("renders product name and submits a research question", () => {
  render(<App />);
  expect(screen.getByText("Deep Search Pro")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("研究问题"), { target: { value: "测试研究" } });
  fireEvent.click(screen.getByLabelText("提交研究"));
  expect(screen.getByText("测试研究", { selector: "article p" })).toBeInTheDocument();
});
