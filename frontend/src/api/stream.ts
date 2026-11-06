export async function streamChat(body:unknown,onToken:(text:string)=>void):Promise<{answer:string;citations:import('../types').Evidence[]}>{
 const response=await fetch('/api/chat/stream',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 if(!response.ok||!response.body)throw Error(await response.text());
 const reader=response.body.getReader(),decoder=new TextDecoder();let buffer='';
 while(true){const {value,done}=await reader.read();buffer+=decoder.decode(value,{stream:!done});let split;
  while((split=buffer.indexOf('\n\n'))>=0){const block=buffer.slice(0,split);buffer=buffer.slice(split+2);const event=block.split('\n').find(s=>s.startsWith('event: '))?.slice(7);const data=block.split('\n').find(s=>s.startsWith('data: '))?.slice(6);if(!data)continue;const payload=JSON.parse(data);if(event==='token')onToken(payload.text);if(event==='error')throw Error(payload.message);if(event==='done')return payload;}
  if(done)throw Error('流式连接提前结束');
 }
}
