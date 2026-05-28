"""v7: 收集详情URL -> 逐个进入 -> 找真实下载"""
import asyncio, os, random, re
from playwright.async_api import async_playwright

SUB_DIR = r"c:\Users\cxx\WorkBuddy\Claw\the_boys_subtitles"
os.makedirs(SUB_DIR, exist_ok=True)

SEASONS = {
    "S3": "https://subf2m.co/subtitles/the-boys-third-season/english",
    "S4": "https://subf2m.co/subtitles/the-boys-season-4/english",
}

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(accept_downloads=True)
        page = await context.new_page()
        
        total = 0
        
        for season_name, list_url in SEASONS.items():
            print(f"\n{'='*50}\n  {season_name}\n{'='*50}")
            
            # 1. 进入列表页收集所有详情URL
            await page.goto(list_url, wait_until="networkidle", timeout=30000)
            await asyncio.sleep(3)
            
            # 用JS提取所有详情链接和标题
            items = await page.evaluate("""() => {
                const results = [];
                // 方法1: li.item 结构
                document.querySelectorAll('li.item').forEach(li => {
                    const a = li.querySelector('a[href*="/english/"]');
                    const dl = li.querySelector('a.download');
                    if (a && dl) {
                        results.push({
                            url: a.href,
                            title: a.textContent.trim(),
                            dlUrl: dl.href
                        });
                    }
                });
                
                // 方法2: 如果上面没找到，尝试其他方式
                if (results.length === 0) {
                    document.querySelectorAll('a').forEach(a => {
                        if (a.href.match(/\\/subtitles\\/.+?\\/\\d+$/) && 
                            !a.href.includes('/english/') &&
                            a.textContent.trim().length > 5) {
                            results.push({
                                url: a.href + '/english',
                                title: a.textContent.trim(),
                                dlUrl: ''
                            });
                        }
                    });
                }
                return results;
            }""")
            
            print(f"  收集到 {len(items)} 个字幕")
            
            # 限制每季下16个（每集2个版本足够）
            items = items[:16]
            
            for i, item in enumerate(items):
                try:
                    title = item.get('title', f'ep{i+1}')[:55]
                    detail_url = item.get('url', '')
                    
                    print(f"  [{i+1:02d}] {title[:40]}...", end="", flush=True)
                    
                    # 2. 进入详情页
                    await page.goto(detail_url, wait_until="networkidle", timeout=20000)
                    await asyncio.sleep(2)
                    
                    # 截图第一个详情页
                    if i == 0:
                        await page.screenshot(path=os.path.join(SUB_DIR, f"_{season_name}_detail.png"))
                        print(f"\n  [截图已保存]")
                    
                    # 3. 在详情页找下载按钮并触发
                    download_obj = None
                    
                    async def on_dl(dl):
                        nonlocal download_obj
                        download_obj = dl
                    
                    page.on("download", on_dl)
                    
                    # 尝试多种点击方式
                    clicked = False
                    
                    # 方式A: 找id包含download的元素
                    for selector in ['#dlbtn', '#downloadButton', 'button#download', 
                                     '.btn-download', '[class*="download-btn"]',
                                     'input[type="submit"][value*="ownload"]',
                                     'a#download']:
                        try:
                            el = await page.query_selector(selector)
                            if el:
                                await el.click()
                                clicked = True
                                break
                        except:
                            continue
                    
                    # 方式B: 如果A没找到，找任何含download文字的按钮/链接
                    if not clicked:
                        try:
                            await page.evaluate("""() => {
                                const els = document.querySelectorAll('a, button, input[type="submit"]');
                                for (const el of els) {
                                    const t = (el.textContent || el.value || '').toLowerCase();
                                    if (t.includes('download') || t.includes('.srt')) {
                                        el.click();
                                        return true;
                                    }
                                }
                                return false;
                            }""")
                            clicked = True
                        except:
                            pass
                    
                    # 等待下载
                    if clicked:
                        for _ in range(12):
                            await asyncio.sleep(1)
                            if download_obj:
                                break
                        
                        page.remove_listener("download", on_dl)
                        
                        if download_obj:
                            safe = re.sub(r'[\\/:*?"<>|]', '_', title[:35])
                            fname = f"{season_name}_{i+1:02d}_{safe}.srt"
                            fpath = os.path.join(SUB_DIR, fname)
                            
                            try:
                                await download_obj.save_as(fpath)
                                sz = os.path.getsize(fpath) if os.path.exists(fpath) else 0
                                
                                if sz > 300:
                                    total += 1
                                    print(f" OK ({sz}B)")
                                else:
                                    print(f" 小({sz}B)")
                                    if os.path.exists(fpath):
                                        os.remove(fpath)
                            except Exception as save_err:
                                print(f" 保存失败:{str(save_err)[:30]}")
                        else:
                            print(f" 无DL事件(可能弹窗?)")
                    else:
                        page.remove_listener("download", on_dl)
                        print(f" 未找到下载按钮")
                    
                    await asyncio.sleep(1.5 + random.random())
                    
                except Exception as e:
                    print(f" ERR:{str(e)[:40]}")
        
        await browser.close()
        
        files = [f for f in os.listdir(SUB_DIR) if f.endswith('.srt')]
        print(f"\n{'='*50}")
        print(f"  完成! 共 {total} 个SRT文件")
        print(f"  文件列表:")
        for f in sorted(files):
            sz = os.path.getsize(os.path.join(SUB_DIR, f))
            print(f"    {f} ({sz}B)")

asyncio.run(main())
