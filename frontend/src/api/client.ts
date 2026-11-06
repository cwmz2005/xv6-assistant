export async function api<T>(path:string,body?:unknown,method?:string):Promise<T>{
 const r=await fetch('/api/'+path,{method:method??(body?'POST':'GET'),headers:{'Content-Type':'application/json'},body:body?JSON.stringify(body):undefined});
 if(!r.ok)throw Error(await r.text());return r.json();
}
