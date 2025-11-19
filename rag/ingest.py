import asyncio
import json
import os
import hashlib
import argparse
import torch
from pathlib import Path
from config import (     # I have to change this for ingetion and retirival
    get_rag_config, 
    get_llm_model_func, 
    get_vision_model_func, 
    get_embedding_func,
    METADATA_FILE,
    OUTPUT_DIR,
    WORKING_DIR
)
from raganything import RAGAnything

# Create directories if they don't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(WORKING_DIR, exist_ok=True)

# Load or initialize processed files metadata
if os.path.exists(METADATA_FILE):
    with open(METADATA_FILE, 'r') as f:
        processed_files = json.load(f)
else:
    processed_files = {}

def get_file_hash(file_path):
    """Generate a hash for a file to detect changes"""
    hasher = hashlib.md5()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def is_file_processed(file_path):
    """Check if file has been processed and hasn't changed"""
    file_path = str(Path(file_path).resolve())
    file_hash = get_file_hash(file_path)
    
    if file_path in processed_files:
        # Check if file has changed since last processing
        if processed_files[file_path]['hash'] == file_hash:
            print(f"✅ Skipping already processed file: {file_path}")
            return True
    return False

def mark_file_processed(file_path):
    """Mark a file as processed in metadata"""
    file_path = str(Path(file_path).resolve())
    file_hash = get_file_hash(file_path)
    
    processed_files[file_path] = {
        'hash': file_hash,
        'processed_at': asyncio.get_event_loop().time(),
        'file_size': os.path.getsize(file_path)
    }
    
    # Save metadata
    with open(METADATA_FILE, 'w') as f:
        json.dump(processed_files, f, indent=2)

async def process_document(rag, file_path):
    """Process a single document with progress indication"""
    print(f"\n🔧 Processing: {file_path}")
    
    try:
        # Ensure output directory exists
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        
        # Process the document with correct parameters
        await rag.process_document_complete(
            file_path=file_path,
            output_dir=OUTPUT_DIR,
            parse_method="ocr",  # Force OCR for maximum compatibility with manuals
            lang="en",           # Document language
            table=True,          # Enable table extraction
            device="cuda:0" if torch.cuda.is_available() else "cpu",
            display_stats=True
        )
        mark_file_processed(file_path)
        print(f"✅ Successfully processed: {file_path}")
        return True
    except Exception as e:
        print(f"❌ Error processing {file_path}: {str(e)}")
        return False

async def process_folder(rag, folder_path, max_workers=2):
    """Process all documents in a folder with deduplication"""
    print(f"📁 Scanning folder: {folder_path}")
    
    # Verify folder exists
    if not os.path.exists(folder_path):
        raise FileNotFoundError(f"Input directory does not exist: {os.path.abspath(folder_path)}")
    
    # Collect all PDF files (add other extensions as needed)
    file_paths = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.lower().endswith(('.pdf', '.docx', '.doc')):
                file_paths.append(os.path.join(root, file))
    
    print(f"🔍 Found {len(file_paths)} documents to process")
    
    # Filter out already processed files
    files_to_process = [
        f for f in file_paths 
        if not is_file_processed(f)
    ]
    
    print(f"🔄 Need to process {len(files_to_process)} new/changed documents")
    
    if not files_to_process:
        print("✨ All documents are already processed!")
        return
    
    # Process files sequentially (RAG-Anything handles concurrency internally)
    for file_path in files_to_process:
        await process_document(rag, file_path)

async def main():
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Ingest documents into RAG-Anything")
    parser.add_argument(
        "--input_dir", 
        type=str, 
        default="../data/raw_pdfs",  # Default to data folder outside rag directory
        help="Directory containing PDFs and other documents to ingest"
    )
    parser.add_argument(
        "--max_workers", 
        type=int, 
        default=2, 
        help="Maximum number of concurrent processing workers"
    )
    args = parser.parse_args()
    
    # Initialize RAG
    rag = RAGAnything(
        config=get_rag_config(),
        llm_model_func=get_llm_model_func(),
        vision_model_func=get_vision_model_func(),
        embedding_func=get_embedding_func(),
    )
    
    # Process documents from the specified input directory
    await process_folder(rag, args.input_dir, max_workers=args.max_workers)
    
    print("\n🎉 Ingestion completed successfully!")

if __name__ == "__main__":
    asyncio.run(main())