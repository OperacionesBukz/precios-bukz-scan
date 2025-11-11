from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
import requests
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Consulta Precios Bukz")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ios-bukz-scan.onrender.com",  # tu frontend en Render
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Templates / static
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Env vars (Render o .env local)
SHOPIFY_API_TOKEN = os.getenv("SHOPIFY_API_TOKEN")
SHOPIFY_STORE = os.getenv("SHOPIFY_STORE")

if not SHOPIFY_API_TOKEN or not SHOPIFY_STORE:
    print("⚠️  WARNING: Faltan variables de entorno SHOPIFY_API_TOKEN o SHOPIFY_STORE")

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/variant_by_sku", response_class=JSONResponse)
def variant_by_sku(sku: str):
    if not sku:
        raise HTTPException(status_code=400, detail="sku is required")

    headers = {
        "Content-Type": "application/json",
        "X-Shopify-Access-Token": SHOPIFY_API_TOKEN
    }

    query = f"""
    {{
      productVariants(first: 1, query: "sku:{sku}") {{
        edges {{
          node {{
            id
            sku
            price
            product {{
              title
            }}
          }}
        }}
      }}
    }}
    """

    url = f"https://{SHOPIFY_STORE}/admin/api/2024-10/graphql.json"

    try:
        r = requests.post(url, json={"query": query}, headers=headers, timeout=10)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error contacting Shopify: {e}")

    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Shopify error {r.status_code}: {r.text}")

    data = r.json()
    edges = data.get("data", {}).get("productVariants", {}).get("edges", [])
    if not edges:
        return JSONResponse({"found": False})

    node = edges[0]["node"]
    return {
        "found": True,
        "title": node["product"]["title"],
        "sku": node["sku"],
        "price": node["price"]
    }
