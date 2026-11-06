import {test,expect} from '@playwright/test';

test('home and lazy-loaded knowledge management',async({page})=>{
 const errors:string[]=[];const requests:string[]=[];
 page.on('pageerror',error=>errors.push(error.message));
 page.on('request',request=>requests.push(request.url()));
 await page.goto('/');
 await expect(page.getByRole('heading',{name:'从一个问题，读懂内核。'})).toBeVisible();
 await expect(page.getByPlaceholder('提问 xv6')).toBeVisible();
 expect(requests.some(url=>url.includes('/KnowledgePanel-'))).toBeFalsy();
 await page.screenshot({path:'../tmp/browser/home.png',fullPage:true});
 await page.getByRole('button',{name:'知识库文档'}).click();
 await expect(page.getByRole('button',{name:'刷新文档'})).toBeVisible();
 await page.getByRole('button',{name:'刷新文档'}).click();
 await expect(page.getByText('系统文档',{exact:true}).first()).toBeVisible();
 await expect(page.getByText('10 条/页',{exact:true})).toBeVisible();
 expect(requests.some(url=>url.includes('/KnowledgePanel-'))).toBeTruthy();
 await page.screenshot({path:'../tmp/browser/knowledge.png',fullPage:true});
 await page.locator('.ant-drawer-close').click();
 await page.getByRole('button',{name:'实验评估',exact:true}).click();
 await expect(page.getByRole('button',{name:'运行实验'})).toBeVisible();
 expect(errors).toEqual([]);
});

test('real streamed chat and citation drawer',async({page,request})=>{
 let sessionId='';
 page.on('response',async response=>{
  if(response.url().endsWith('/api/sessions')&&response.request().method()==='POST')sessionId=(await response.json()).id;
 });
 try{
  await page.goto('/');
  await page.getByPlaceholder('提问 xv6').fill('walkaddr 为什么检查 PTE_U？请简短回答并引用源码。');
  await page.getByRole('button',{name:/^发送/}).click();
  const citation=page.getByRole('button',{name:/kernel\/vm.c:/}).first();
  await expect(citation).toBeVisible({timeout:160000});
  await expect(page.locator('.message.assistant .inline-citation').first()).toBeVisible();
  await expect(page.locator('.message.assistant')).not.toContainText(/[0-9a-f]{64}/);
  await page.screenshot({path:'../tmp/browser/chat.png',fullPage:true,animations:'disabled'});
  await citation.click();
  await expect(page.getByRole('dialog')).toBeVisible();
  await expect(page.locator('pre').filter({hasText:'PTE_U'}).last()).toBeVisible();
  await page.screenshot({path:'../tmp/browser/citation.png',fullPage:true,animations:'disabled'});
 }finally{if(sessionId)await request.delete('/api/sessions/'+sessionId);}
});
