/* Unified offline catalog store shared by LIMS and GIS tabs/windows. */
(function(global){
  "use strict";
  const DB_NAME="agri-unified-catalog",STORE="produce",META="metadata",CHANNEL="agri-catalog-sync";
  const channel=typeof BroadcastChannel!=="undefined"?new BroadcastChannel(CHANNEL):null;
  let dbPromise=null;
  const masterCatalog=((global.AGRI_SHARED&&global.AGRI_SHARED.catalog)||[]).slice();
  function mergeMaster(rows){const merged=new Map(masterCatalog.map(item=>[item.id,Object.assign({catalogSource:"shared-seed"},item)]));(rows||[]).forEach(item=>merged.set(item.id,item));return Array.from(merged.values()).sort((a,b)=>a.name.localeCompare(b.name));}
  let memoryCatalog=mergeMaster([]);
  function open(){
    if(dbPromise)return dbPromise;
    dbPromise=new Promise((resolve,reject)=>{
      if(!global.indexedDB){reject(new Error("IndexedDB unavailable"));return;}
      const request=indexedDB.open(DB_NAME,1);
      request.onupgradeneeded=()=>{const db=request.result;if(!db.objectStoreNames.contains(STORE))db.createObjectStore(STORE,{keyPath:"id"});if(!db.objectStoreNames.contains(META))db.createObjectStore(META,{keyPath:"key"});};
      request.onsuccess=()=>resolve(request.result);request.onerror=()=>reject(request.error);
    });
    return dbPromise;
  }
  async function request(storeName,mode,action){
    const db=await open();return new Promise((resolve,reject)=>{const tx=db.transaction(storeName,mode),req=action(tx.objectStore(storeName));req.onsuccess=()=>resolve(req.result);req.onerror=()=>reject(req.error);});
  }
  async function persistedRows(){const rows=await request(STORE,"readonly",store=>store.getAll());return rows.sort((a,b)=>a.name.localeCompare(b.name));}
  async function all(){try{const rows=await persistedRows();memoryCatalog=mergeMaster(rows);return memoryCatalog.slice();}catch(error){console.warn("Catalog database unavailable; using shared fallback",error);return mergeMaster(memoryCatalog);}}
  async function seed(){
    const shared=global.AGRI_SHARED;if(!shared)return memoryCatalog;
    memoryCatalog=mergeMaster([]);
    try{
      const version=await request(META,"readonly",store=>store.get("catalog-version")),rows=await persistedRows();
      if(version&&version.value===shared.version&&rows.length){memoryCatalog=mergeMaster(rows);return memoryCatalog.slice();}
      const db=await open();await new Promise((resolve,reject)=>{const tx=db.transaction([STORE,META],"readwrite"),produce=tx.objectStore(STORE),meta=tx.objectStore(META);produce.clear();shared.catalog.forEach(item=>produce.put(Object.assign({catalogSource:"shared-seed"},item)));meta.put({key:"catalog-version",value:shared.version,seededAt:new Date().toISOString()});tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);});
      return persistedRows();
    }catch(error){console.warn("Catalog seed failed; synchronous fallback remains active",error);return memoryCatalog.slice();}
  }
  function notify(){channel&&channel.postMessage({type:"catalog-changed",at:Date.now()});global.dispatchEvent(new CustomEvent("agri-catalog-changed"));}
  async function upsert(item){memoryCatalog=[...memoryCatalog.filter(row=>row.id!==item.id),item].sort((a,b)=>a.name.localeCompare(b.name));try{await request(STORE,"readwrite",store=>store.put(Object.assign({catalogSource:"local"},item)));}catch(error){console.warn("Catalog upsert retained in memory only",error);}notify();return item;}
  async function upsertMany(items){const incoming=new Map(items.map(item=>[item.id,item]));memoryCatalog=memoryCatalog.filter(row=>!incoming.has(row.id)).concat(items).sort((a,b)=>a.name.localeCompare(b.name));try{const db=await open();await new Promise((resolve,reject)=>{const tx=db.transaction(STORE,"readwrite"),store=tx.objectStore(STORE);items.forEach(item=>store.put(Object.assign({catalogSource:"local"},item)));tx.oncomplete=resolve;tx.onerror=()=>reject(tx.error);});}catch(error){console.warn("Catalog batch retained in memory only",error);}notify();return items;}
  async function remove(id){memoryCatalog=memoryCatalog.filter(row=>row.id!==id);try{await request(STORE,"readwrite",store=>store.delete(id));}catch(error){console.warn("Catalog delete applied in memory only",error);}notify();}
  function subscribe(callback){const refresh=()=>all().then(rows=>callback(rows.length?rows:memoryCatalog.slice())).catch(()=>callback(memoryCatalog.slice())),listener=event=>{if(event.data?.type==="catalog-changed")refresh();};channel&&channel.addEventListener("message",listener);global.addEventListener("agri-catalog-changed",refresh);return()=>{channel&&channel.removeEventListener("message",listener);global.removeEventListener("agri-catalog-changed",refresh);};}
  const ready=Promise.resolve(memoryCatalog.slice()).then(fallback=>{global.dispatchEvent(new CustomEvent("agri-catalog-fallback",{detail:fallback}));return seed();});
  global.AGRI_DATA_STORE={version:2,ready,all,upsert,upsertMany,remove,subscribe,fallback:function(){return memoryCatalog.slice();}};
})(window);
