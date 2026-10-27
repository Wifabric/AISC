import {beforeEach,describe,it,expect,vi} from "vitest";
import {createPinia,setActivePinia} from "pinia";
import {useExtensionsStore} from "../extensions";
import {extensionsCall} from "../../lib/ipc";
vi.mock("../../lib/ipc",()=>({extensionsCall:vi.fn()}));
vi.mock("@tauri-apps/plugin-clipboard-manager",()=>({writeText:vi.fn()}));
const call=vi.mocked(extensionsCall);
beforeEach(()=>{setActivePinia(createPinia());call.mockReset();});
function setup(){const s=useExtensionsStore();s.setContext("/ws","r1");return s;}
describe("extension operation recovery",()=>{
 it("keeps original failure after successful SSOT refresh and retries original parameters",async()=>{
  call.mockImplementation(async p=>{if(p.op==="plugin-install")throw new Error("upstream failed token=secret");return {items:[]};});
  const s=setup();s.kind="plugins";await s.pluginAction("plugin-install","p@m");
  expect(s.error).toContain("upstream failed");expect(s.operationLog).toHaveLength(1);
  expect(s.operationLog[0].diagnostic).not.toContain("secret");
  const id=s.operationLog[0].operationId;
  call.mockResolvedValue({items:[]});await s.retryOperation(id);
  expect(call.mock.calls.filter(([p])=>p.op==="plugin-install")).toHaveLength(2);
  expect(s.operationLog[s.operationLog.length - 1]).toMatchObject({status:"success",attempt:2,id:"p@m"});
 });
 it("retries only explicit failed children from a partially completed group",async()=>{
  call.mockImplementation(async p=>p.op==="skill-install-group"?{total:2,completed:1,items:[{spec:"o/r:a",status:"installed"},{spec:"o/r:b",status:"failed",error:"network down"}]}:{items:[]});
  const s=setup();s.marketSkills=[{kind:"market-skill",id:"o/r:a",name:"a",repo:"o/r",directory:"a"},{kind:"market-skill",id:"o/r:b",name:"b",repo:"o/r",directory:"b"}];
  await s.installSkillGroup(s.marketSkillGroups[0]!);
  expect(s.operationLog.map(x=>x.status)).toEqual(["success","failed"]);
  await s.retryOperation(s.operationLog[1]!.operationId);
  expect(call.mock.calls.filter(([p])=>p.op==="skill-install").map(([p])=>p.spec)).toEqual(["o/r:b"]);
 });
 it("continues group uninstall after one child fails and retries only that child",async()=>{
  call.mockImplementation(async p=>{if(p.op==="delete"&&p.id==="a")throw new Error("delete failed");return {items:[]};});
  const s=setup();s.itemsByKind.skills=[{kind:"skills",id:"a",name:"a",repo:"o/r",directory:"a"},{kind:"skills",id:"b",name:"b",repo:"o/r",directory:"b"}];
  await s.removeSkillGroup(s.installedSkillGroups[0]!);
  expect(call.mock.calls.filter(([p])=>p.op==="delete").map(([p])=>p.id)).toEqual(["a","b"]);
  expect(s.operationLog.map(x=>x.status)).toEqual(["failed","success"]);
 });
 it("does not offer blind retry after timeout or after context changes",async()=>{
  call.mockImplementation(async p=>{if(p.op!=="list")throw new Error("request timed out");return {items:[]};});
  const s=setup();await s.installSkill("o/r:a");
  expect(s.operationLog[0].status).toBe("unknown");expect(s.canRetryOperation(s.operationLog[0].operationId)).toBe(false);
  s.setContext("/new","r2");expect(s.operationLog).toEqual([]);
 });
 it("bounds log to 100 rows and serializes repeated clicks",async()=>{
  let finish!:(v:any)=>void;call.mockImplementation(p=>p.op==="plugin-install"?new Promise(r=>{finish=r;}):Promise.resolve({items:[]}));
  const s=setup();const pending=s.pluginAction("plugin-install","p@m");await s.pluginAction("plugin-install","p@m");
  expect(call.mock.calls.filter(([p])=>p.op==="plugin-install")).toHaveLength(1);finish({});await pending;
  call.mockResolvedValue({items:[]});for(let n=0;n<102;n++)await s.pluginAction("plugin-install",`${n}@m`);
  expect(s.operationLog).toHaveLength(100);expect(s.operationLog[0].id).toBe("2@m");
 });
 it("does not continue an old multi-item mutation in a new context",async()=>{
  let finish!:(v:any)=>void;
  call.mockImplementation(p=>p.op==="delete"?new Promise(r=>{finish=r;}):Promise.resolve({items:[]}));
  const s=setup();s.itemsByKind.skills=[{kind:"skills",id:"a",name:"a",repo:"o/r",directory:"a"},{kind:"skills",id:"b",name:"b",repo:"o/r",directory:"b"}];
  const pending=s.removeSkillGroup(s.installedSkillGroups[0]!);s.setContext("/new","r2");finish({});await pending;
  expect(call.mock.calls.filter(([p])=>p.op==="delete")).toHaveLength(1);expect(s.operationLog).toEqual([]);
 });
 it("caps UTF-8 diagnostics and copies a redacted record",async()=>{
  call.mockImplementation(async p=>{if(p.op!=="list")throw new Error("token=very-secret "+"错".repeat(9000));return {items:[]};});
  const s=setup();await s.installSkill("o/r:a");const row=s.operationLog[0]!;
  expect(new TextEncoder().encode(row.diagnostic).length).toBeLessThanOrEqual(8192);
  const {writeText}=await import("@tauri-apps/plugin-clipboard-manager");
  await s.copyOperationDiagnostic(row.operationId);
  expect(vi.mocked(writeText).mock.calls[vi.mocked(writeText).mock.calls.length - 1]?.[0]).not.toContain("very-secret");
 });

 it("matches group results when SSOT canonicalizes repository casing",async()=>{
  call.mockImplementation(async p=>p.op==="skill-install-group"?{total:1,completed:1,items:[{spec:"Owner/Repo:a",status:"installed"}]}:{items:[]});
  const s=setup();s.marketSkills=[{kind:"market-skill",id:"owner/repo:a",name:"a",repo:"owner/repo",directory:"a"}];
  await s.installSkillGroup(s.marketSkillGroups[0]!);expect(s.operationLog[0].status).toBe("success");
 });

 it("keeps MCP failure recovery in the same pipeline",async()=>{
  call.mockImplementation(async p=>{if(p.op==="mcp-market-install")throw new Error("MCP HTTP 502");return {items:[]};});
  const s=setup();s.kind="mcp";await s.installMcpMarket("server/pdf");
  const row=s.operationLog[0]!;expect(row).toMatchObject({kind:"mcp",action:"install",status:"failed"});
  call.mockResolvedValue({items:[]});await s.retryOperation(row.operationId);
  expect(call.mock.calls.filter(([p])=>p.op==="mcp-market-install").map(([p])=>p.id)).toEqual(["server/pdf","server/pdf"]);
 });
 it("does not offer failed-item retry for blocked preflight results",async()=>{
  call.mockImplementation(async p=>p.op==="skill-install-group"?{total:1,completed:0,items:[{spec:"o/r:a",status:"blocked",error:"source preflight failed"}]}:{items:[]});
  const s=setup();s.marketSkills=[{kind:"market-skill",id:"o/r:a",name:"a",repo:"o/r",directory:"a"}];await s.installSkillGroup(s.marketSkillGroups[0]!);
  expect(s.canRetryOperation(s.operationLog[0]!.operationId)).toBe(false);
 });

 it("classifies structured localized CLI timeout as unknown",async()=>{
  call.mockImplementation(async p=>{if(p.op!=="list")throw {code:"WB_ERR_CLI_TIMEOUT",message:"AISC CLI 响应超时"};return {items:[]};});
  const s=setup();await s.installSkill("o/r:a");expect(s.operationLog[0].status).toBe("unknown");expect(s.canRetryOperation(s.operationLog[0].operationId)).toBe(false);
 });
 it("does not leak quoted credential suffixes",async()=>{
  call.mockImplementation(async p=>{if(p.op!=="list")throw new Error('password="two word-secret" token=abc');return {items:[]};});
  const s=setup();await s.installSkill("o/r:a");expect(s.operationLog[0].diagnostic).not.toContain("word-secret");
 });
 it("keeps explicit source failures retryable but blocked results separate",async()=>{
  call.mockImplementation(async p=>p.op==="skill-install-group"?{total:1,completed:0,items:[{spec:"o/r:a",status:"source_failed",error:"network down"}]}:{items:[]});
  const s=setup();s.marketSkills=[{kind:"market-skill",id:"o/r:a",name:"a",repo:"o/r",directory:"a"}];await s.installSkillGroup(s.marketSkillGroups[0]!);
  expect(s.canRetryOperation(s.operationLog[0]!.operationId)).toBe(true);
 });
 it("drops an old group error after a context switch during refresh",async()=>{
  let complete!:(v:any)=>void;call.mockImplementation(p=>p.op==="skill-install-group"?Promise.resolve({total:1,completed:0,items:[{spec:"o/r:a",status:"failed",error:"old failure"}]}):new Promise(r=>{complete=r;}));
  const s=setup();s.marketSkills=[{kind:"market-skill",id:"o/r:a",name:"a",repo:"o/r",directory:"a"}];const pending=s.installSkillGroup(s.marketSkillGroups[0]!);
  await Promise.resolve();await Promise.resolve();await Promise.resolve();s.setContext("/new","r2");complete({items:[]});await pending;expect(s.error).toBeNull();
 });

});
