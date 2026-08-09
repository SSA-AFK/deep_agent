import { fireEvent, render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import App from "./App";

vi.mock("./api/client", () => ({ api: { createTask: vi.fn().mockResolvedValue({ thread_id: "test-1" }), upload: vi.fn().mockResolvedValue({ files: [] }), confirm: vi.fn().mockResolvedValue({}) } }));

test("renders product name and submits a research question", async () => {
  render(<App />);
  expect(screen.getByText("Deep Search Pro")).toBeInTheDocument();
  expect(screen.getByText("服务状态")).toBeInTheDocument();
  expect(screen.getByText("添加附件")).toBeInTheDocument();
  fireEvent.change(screen.getByLabelText("研究问题"), { target: { value: "测试研究" } });
  fireEvent.click(screen.getByLabelText("提交研究"));
  expect(await screen.findByText("测试研究", { selector: "article p" })).toBeInTheDocument();
  fireEvent.click(screen.getByText("确认并开始"));
  expect(await screen.findByText("研究正在进行")).toBeInTheDocument();
  expect(screen.getAllByText("演示来源")).toHaveLength(2);
  fireEvent.click(screen.getByText("查看模拟报告"));
  expect(screen.getByText("优先选择可观察、可接管的工作流")).toBeInTheDocument();
});
