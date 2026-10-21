"""Optional local backend smoke CLI; does not access any network."""
import argparse
import json
from ai.llm_engine import GGUFEngine
from settings import Settings

def main():
    """Check GGUF loading, inference and JSON output using synthetic text."""
    parser=argparse.ArgumentParser();parser.add_argument('--model',required=True)
    args=parser.parse_args();engine=GGUFEngine(Settings(model_path=args.model))
    try:print(json.dumps(engine.generate_json('Yalnızca {"status":"ok"} üret.'),ensure_ascii=False))
    finally:engine.unload()

if __name__=='__main__':main()
