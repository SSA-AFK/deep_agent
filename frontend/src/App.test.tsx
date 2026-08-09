import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import App from "./App";

test("renders product name and submits a research question", () => {
  render(<App />);
  expect(screen.getByText("Deep Search Pro")).toBeInTheDocument();
  expect(screen.getByText("服务状态")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("研究问题"), { target: { value: "测试研究" } });
  fireEvent.click(screen.getByLabelText("提交研究"));
  expect(screen.getByText("测试研究", { selector: "article p" })).toBeInTheDocument();
  fireEvent.click(screen.getByText("确认并开始"));
  expect(screen.getByText("研究正在进行")).toBeInTheDocument();
  expect(screen.getAllByText("演示来源")).toHaveLength(2);
  fireEvent.click(screen.getByText("查看模拟报告"));
  expect(screen.getByText("优先选择可观察、可接管的工作流")).toBeInTheDocument();
});
