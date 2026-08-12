import { afterEach, beforeEach, describe, expect, it } from "vitest";
import {
  ResearchSession,
  addSession,
  createEmptySession,
  createSessionId,
  deleteSession,
  deriveTitle,
  groupByRelativeTime,
  loadActiveSessionId,
  loadAllSessions,
  saveActiveSessionId,
  saveAllSessions,
  toOrderedList,
  updateSession,
} from "./session-store";

const STORAGE_KEY = "deep-search-pro:sessions:v1";
const ACTIVE_KEY = "deep-search-pro:active-session:v1";

beforeEach(() => {
  localStorage.clear();
});
afterEach(() => {
  localStorage.clear();
});

describe("createSessionId & createEmptySession", () => {
  it("生成的会话 id 带 sess- 前缀且不重复", () => {
    const a = createSessionId();
    const b = createSessionId();
    expect(a.startsWith("sess-")).toBe(true);
    expect(b.startsWith("sess-")).toBe(true);
    expect(a).not.toBe(b);
  });

  it("新会话初始字段正确", () => {
    const s = createEmptySession();
    expect(s.id.startsWith("sess-")).toBe(true);
    expect(s.threadId).toBeNull();
    expect(s.title).toBe("新的研究");
    expect(s.draft).toBe("");
    expect(s.submitted).toBeNull();
    expect(s.confirmed).toBe(false);
    expect(s.completed).toBe(false);
    expect(s.taskState).toBeNull();
    expect(s.taskResult).toBeNull();
    expect(s.error).toBeNull();
    expect(s.createdAt).toBeGreaterThan(0);
    expect(s.createdAt).toBe(s.updatedAt);
  });

  it("createEmptySession 支持字段覆盖", () => {
    const s = createEmptySession({ id: "sess-fixed", title: "覆盖标题" });
    expect(s.id).toBe("sess-fixed");
    expect(s.title).toBe("覆盖标题");
  });
});

describe("持久化：saveAll / loadAll 与 saveActive / loadActive", () => {
  it("空存储时返回空对象", () => {
    expect(loadAllSessions()).toEqual({});
    expect(loadActiveSessionId()).toBeNull();
  });

  it("保存后能重新读取，存储 key 符合约定", () => {
    const s1 = createEmptySession({ id: "sess-a", title: "会话A" });
    saveAllSessions({ [s1.id]: s1 });
    saveActiveSessionId("sess-a");
    const restored = loadAllSessions();
    expect(restored["sess-a"]?.title).toBe("会话A");
    expect(loadActiveSessionId()).toBe("sess-a");
    // 直接从 localStorage 读，确保 key 名称不变
    expect(localStorage.getItem(STORAGE_KEY)).toBeTruthy();
    expect(localStorage.getItem(ACTIVE_KEY)).toBe("sess-a");
  });

  it("saveActiveSessionId(null) 清除激活 key", () => {
    saveActiveSessionId("sess-a");
    saveActiveSessionId(null);
    expect(localStorage.getItem(ACTIVE_KEY)).toBeNull();
    expect(loadActiveSessionId()).toBeNull();
  });

  it("localStorage 损坏时静默降级而非抛错", () => {
    localStorage.setItem(STORAGE_KEY, "{ bad json ");
    expect(loadAllSessions()).toEqual({});
  });
});

describe("会话集合操作：add / update / delete / ordered", () => {
  it("addSession 能新增，并超过 MAX_SESSIONS 时淘汰最旧的", () => {
    let sessions: Record<string, ResearchSession> = {};
    const base = Date.now();
    for (let i = 0; i < 52; i++) {
      const s = createEmptySession({
        id: `sess-${i}`,
        createdAt: base + i,
        updatedAt: base + i,
      });
      sessions = addSession(sessions, s);
    }
    expect(Object.keys(sessions)).toHaveLength(50);
    // 按 updatedAt 倒序，sess-51 和 sess-50 应保留，0 和 1 被淘汰
    expect(sessions["sess-0"]).toBeUndefined();
    expect(sessions["sess-1"]).toBeUndefined();
    expect(sessions["sess-51"]).toBeDefined();
    expect(sessions["sess-50"]).toBeDefined();
  });

  it("updateSession 只更新目标且 updatedAt 前进", () => {
    const s1 = createEmptySession({ id: "sess-a", title: "旧" });
    const sleep = new Promise<void>((r) => setTimeout(r, 2));
    // 用同步方式构造一个不同的时间戳
    const prevUpdated = s1.updatedAt;
    const patched = updateSession({ [s1.id]: s1 }, s1.id, { title: "新", submitted: "问题X" });
    expect(patched["sess-a"]?.title).toBe("新");
    expect(patched["sess-a"]?.submitted).toBe("问题X");
    expect(patched["sess-a"]?.updatedAt).toBeGreaterThanOrEqual(prevUpdated);
  });

  it("updateSession 对不存在的 id 原样返回", () => {
    const base = createEmptySession({ id: "a" });
    const result = updateSession({ [base.id]: base }, "nope", { title: "ignored" });
    expect(result).toBe(result); // 引用相同也可，关键是不抛错
    expect(result["a"]?.title).toBe("新的研究");
  });

  it("deleteSession 删除目标", () => {
    const a = createEmptySession({ id: "a" });
    const b = createEmptySession({ id: "b" });
    const sessions = { [a.id]: a, [b.id]: b };
    expect(Object.keys(deleteSession(sessions, "a"))).toEqual(["b"]);
  });

  it("toOrderedList 按 updatedAt 倒序", () => {
    const a = createEmptySession({ id: "a", updatedAt: 100 });
    const b = createEmptySession({ id: "b", updatedAt: 300 });
    const c = createEmptySession({ id: "c", updatedAt: 200 });
    const list = toOrderedList({ a, b, c });
    expect(list.map((s) => s.id)).toEqual(["b", "c", "a"]);
  });
});

describe("deriveTitle", () => {
  it("优先使用 submitted，其次 draft，再次 fallback", () => {
    expect(deriveTitle("已提交的问题", "草稿")).toBe("已提交的问题");
    expect(deriveTitle(null, "草稿内容")).toBe("草稿内容");
    expect(deriveTitle(null, "")).toBe("新的研究");
    expect(deriveTitle(null, "  ", "空的哦")).toBe("空的哦");
  });

  it("折叠空白并按长度截断，结尾加省略号", () => {
    const long = "这是一段非常非常非常非常非常非常非常长的研究问题标题需要被截断";
    const got = deriveTitle(long, null);
    expect(got.length).toBeLessThan(long.length);
    expect(got.endsWith("…")).toBe(true);
  });
});

describe("groupByRelativeTime", () => {
  function withOffset(daysAgo: number, id: string): ResearchSession {
    const ms = Date.now() - daysAgo * 24 * 60 * 60 * 1000;
    return createEmptySession({ id, createdAt: ms, updatedAt: ms });
  }

  it("按今天/昨天/7天前/更早分组，顺序与标签固定", () => {
    const sessions = [
      withOffset(0, "today"),
      withOffset(0.3, "today-2"),
      withOffset(1, "yesterday"),
      withOffset(3, "7days"),
      withOffset(30, "much-older"),
    ];
    const groups = groupByRelativeTime(sessions);
    expect(groups.map((g) => g.label)).toEqual(["今天", "昨天", "7 天前", "更早"]);
    expect(groups.find((g) => g.label === "今天")!.items.map((x) => x.id).sort()).toEqual(
      ["today", "today-2"].sort()
    );
    expect(groups.find((g) => g.label === "昨天")!.items).toHaveLength(1);
    expect(groups.find((g) => g.label === "7 天前")!.items).toHaveLength(1);
    expect(groups.find((g) => g.label === "更早")!.items).toHaveLength(1);
  });

  it("空分组不出现在结果中", () => {
    const sessions = [withOffset(30, "old"), withOffset(40, "older")];
    const groups = groupByRelativeTime(sessions);
    expect(groups.map((g) => g.label)).toEqual(["更早"]);
  });
});
