import {beforeEach,it,expect,vi} from "vitest";
import {setActivePinia,createPinia} from "pinia";
import {useExtensionsStore} from "../extensions";
import {extensionsCall} from "../../lib/ipc";
vi.mock("../../lib/ipc",()=>({extensionsCall:vi.fn()}));
const call=vi.mocked(extensionsCall);
beforeEach(()=>{setActivePinia(createPinia());call.mockReset();});
it.each([["skills","skill-search"],["mcp","mcp-search"],["plugins","plugin-search"]] as const)("discovers %s through existing search",async(kind,op)=>{
 call.mockResolvedValue({items:[]});const s=useExtensionsStore();s.setContext("/ws","r");await s.discoverRecommendation(kind,"query");expect(s.kind).toBe(kind);expect(call).toHaveBeenCalledWith(expect.objectContaining({op,query:"query"}));
});
it("ignores the older response and its finally during an overlapping query",async()=>{
 let a!:(v:any)=>void,b!:(v:any)=>void;call.mockImplementation(p=>new Promise(r=>{if(p.query==="a")a=r;else b=r;}));const s=useExtensionsStore();s.setContext("/ws","r");
 const first=s.searchSkills("a");const second=s.searchSkills("b");a({items:[{id:"a"}],cache:{cached:true}});await first;expect(s.marketBusy).toBe(true);expect(s.marketSkills).toEqual([]);
 b({items:[{id:"b"}],cache:{cached:false}});await second;expect(s.marketSkills[0].id).toBe("b");expect(s.marketBusy).toBe(false);
});
it("invalidates an in-flight response when search is cleared",async()=>{
 let done!:(v:any)=>void;call.mockImplementation(()=>new Promise(r=>{done=r;}));const s=useExtensionsStore();s.setContext("/ws","r");const pending=s.searchMcp("pdf");s.clearMarketResults("mcp");done({items:[{id:"old"}],cache:{cached:true}});await pending;expect(s.marketMcp).toEqual([]);expect(s.marketCacheByKind.mcp).toBeNull();
});
it("makes local discovery offline safe and clears installed rows from old context",async()=>{
 const s=useExtensionsStore();await s.discoverRecommendation("plugins","superpowers");expect(call).not.toHaveBeenCalled();s.setContext("/a","r1");s.itemsByKind.skills=[{kind:"skills",id:"old",name:"old"}];s.setContext("/b","r2");expect(s.itemsByKind.skills).toEqual([]);
});

it("does not let marketplace list completion unlock a pending plugin search",async()=>{
 let list!:(v:any)=>void,search!:(v:any)=>void;call.mockImplementation(p=>new Promise(r=>{if(p.op==="plugin-market-list")list=r;else search=r;}));
 const s=useExtensionsStore();s.setContext("/ws","r");s.kind="plugins";const a=s.loadPluginMarkets();const b=s.searchPlugins("new");list({items:[]});await a;expect(s.marketBusy).toBe(true);search({items:[]});await b;expect(s.marketBusy).toBe(false);
});

it("keeps marketplace list errors separate from search diagnostics",async()=>{
 let search!:(v:any)=>void,fail!:(v:any)=>void;call.mockImplementation(p=>new Promise((r,j)=>{if(p.op==="plugin-market-list")fail=j;else search=r;}));
 const s=useExtensionsStore();s.setContext("/ws","r");s.kind="plugins";const a=s.searchPlugins("new");const b=s.loadPluginMarkets();search({items:[{id:"new"}]});await a;fail(new Error("list failure"));await b;expect(s.error).toBeNull();expect(s.pluginMarketsError).toContain("list failure");
});
it("ignores stale marketplace lists and their busy cleanup",async()=>{
 const done:Array<(v:any)=>void>=[];call.mockImplementation(()=>new Promise(r=>{done.push(r);}));const s=useExtensionsStore();s.setContext("/ws","r");s.kind="plugins";
 const a=s.loadPluginMarkets(),b=s.loadPluginMarkets();done[0]!({items:[{id:"old"}]});await a;expect(s.marketBusy).toBe(true);expect(s.pluginMarkets).toEqual([]);done[1]!({items:[{id:"new"}]});await b;expect(s.pluginMarkets[0].id).toBe("new");
});

it("refreshes installed facts for a recommendation's target kind",async()=>{
 call.mockImplementation(async p=>p.op==="list"?{items:[{kind:"mcp",id:"installed",name:"installed"}]}:{items:[]});const s=useExtensionsStore();s.setContext("/ws","r");await s.discoverRecommendation("mcp","context7");expect(s.itemsByKind.mcp[0]?.id).toBe("installed");
});

it("does not start an old recommendation search after a newer search or clear",async()=>{
 let finish!:(v:any)=>void;
 call.mockImplementation(p=>p.op==="list"?new Promise(r=>{finish=r;}):Promise.resolve({items:[{id:"new"}]}));
 const s=useExtensionsStore();s.setContext("/ws","r");
 const old=s.discoverRecommendation("mcp","old");await s.searchMcp("new");
 finish({items:[]});await old;
 expect(call.mock.calls.some(([p])=>p.query==="old")).toBe(false);
 expect(s.marketMcp[0]?.id).toBe("new");
 const pending=s.discoverRecommendation("mcp","cleared");s.clearMarketResults("mcp");finish({items:[]});await pending;
 expect(call.mock.calls.some(([p])=>p.query==="cleared")).toBe(false);
 expect(s.marketMcp).toEqual([]);
});
