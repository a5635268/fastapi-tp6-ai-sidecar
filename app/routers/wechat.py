from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.wechat import process_wechat_url

router = APIRouter(prefix="/wechat", tags=["微信功能"])

class WechatArticleRequest(BaseModel):
    url: str

@router.post("/parse", summary="解析微信公众号文章")
async def parse_article(req: WechatArticleRequest):
    """
    接收微信公众号文章的 URL 并解析提取为 Markdown 格式和相关元数据
    """
    try:
        result = await process_wechat_url(req.url)
        return {"code": 0, "message": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析错误: {str(e)}")

@router.get("/parse", summary="解析微信公众号文章 (GET)")
async def parse_article_get(url: str = Query(..., description="微信文章链接")):
    """
    接收微信公众号文章的 URL 并解析提取为 Markdown 格式和相关元数据
    """
    try:
        result = await process_wechat_url(url)
        return {"code": 0, "message": "success", "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"解析错误: {str(e)}")
