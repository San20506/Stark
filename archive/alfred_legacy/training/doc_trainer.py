"""
ALFRED Code Brain - Documentation Training Pipeline
Scrape documentation and create fine-tuning datasets for domain-specific training.

Workflow:
1. Scrape documentation from URLs
2. Extract code examples and explanations
3. Format as instruction-response pairs
4. Save as JSONL for LoRA fine-tuning
"""

import os
import sys
import json
import re
import logging
from typing import List, Dict, Tuple
from dataclasses import dataclass

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.doc_scraper import get_doc_scraper

logger = logging.getLogger("DocTrainer")


@dataclass
class TrainingExample:
    """A single training example."""
    instruction: str
    response: str
    source: str


class DocTrainingPipeline:
    """
    Create training datasets from documentation.
    
    Usage:
        pipeline = DocTrainingPipeline()
        
        # Add PyTorch docs
        pipeline.scrape_and_process([
            "https://pytorch.org/docs/stable/torch.html",
            "https://pytorch.org/docs/stable/nn.html",
        ])
        
        # Save dataset
        pipeline.save_jsonl("data/pytorch_training.jsonl")
    """
    
    OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "training")
    
    def __init__(self):
        self.scraper = get_doc_scraper()
        self.examples: List[TrainingExample] = []
        os.makedirs(self.OUTPUT_DIR, exist_ok=True)
    
    def scrape_and_process(self, urls: List[str]):
        """Scrape URLs and extract training examples."""
        for url in urls:
            logger.info(f"Processing: {url}")
            content = self.scraper.scrape(url, max_length=50000)
            
            if content.startswith("[Error"):
                logger.warning(f"Failed to scrape: {url}")
                continue
            
            # Extract examples from content
            examples = self._extract_examples(content, url)
            self.examples.extend(examples)
            logger.info(f"  Extracted {len(examples)} examples")
    
    def _extract_examples(self, content: str, source: str) -> List[TrainingExample]:
        """Extract instruction-response pairs from documentation."""
        examples = []
        
        # Pattern 1: Code blocks with explanations
        code_blocks = self._extract_code_blocks(content)
        for code, context in code_blocks:
            if len(code) > 50 and len(context) > 20:
                examples.append(TrainingExample(
                    instruction=f"Write PyTorch code to: {context}",
                    response=code,
                    source=source
                ))
        
        # Pattern 2: Function signatures with descriptions
        functions = self._extract_functions(content)
        for func_name, description, signature in functions:
            if len(description) > 30:
                examples.append(TrainingExample(
                    instruction=f"Explain the PyTorch function: {func_name}",
                    response=f"{description}\n\nSignature:\n```python\n{signature}\n```",
                    source=source
                ))
        
        # Pattern 3: Q&A style from headers
        qa_pairs = self._extract_qa_from_headers(content)
        examples.extend(qa_pairs)
        
        return examples
    
    def _extract_code_blocks(self, content: str) -> List[Tuple[str, str]]:
        """Extract code blocks with surrounding context."""
        results = []
        
        # Look for Python code patterns
        lines = content.split('\n')
        code_block = []
        context_lines = []
        in_code = False
        
        for i, line in enumerate(lines):
            # Detect code start (indented or has common code patterns)
            is_code_line = (
                line.startswith('>>>') or
                line.startswith('    ') or
                'import torch' in line or
                'torch.' in line or
                '= nn.' in line
            )
            
            if is_code_line:
                if not in_code:
                    # Get context from previous lines
                    context_lines = [l for l in lines[max(0, i-3):i] if l.strip()]
                in_code = True
                code_block.append(line.lstrip('>>> ').rstrip())
            else:
                if in_code and code_block:
                    code = '\n'.join(code_block)
                    context = ' '.join(context_lines)[:200]
                    if code.strip():
                        results.append((code, context))
                in_code = False
                code_block = []
        
        return results
    
    def _extract_functions(self, content: str) -> List[Tuple[str, str, str]]:
        """Extract function documentation."""
        results = []
        
        # Pattern: function_name(args) followed by description
        pattern = r'(torch\.\w+|nn\.\w+)\s*\((.*?)\)\s*[:\-–]\s*(.+?)(?=\n\n|\Z)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        for func_name, args, description in matches:
            signature = f"{func_name}({args})"
            desc_clean = description.strip()[:500]
            if len(desc_clean) > 30:
                results.append((func_name, desc_clean, signature))
        
        return results
    
    def _extract_qa_from_headers(self, content: str) -> List[TrainingExample]:
        """Extract Q&A pairs from section headers."""
        results = []
        
        lines = content.split('\n')
        current_header = None
        current_content = []
        
        for line in lines:
            # Detect headers (all caps or title case with specific keywords)
            is_header = (
                line.isupper() and len(line) > 5 or
                any(kw in line.lower() for kw in ['how to', 'example', 'usage', 'tutorial'])
            )
            
            if is_header and len(line.strip()) < 100:
                if current_header and current_content:
                    content_text = '\n'.join(current_content)[:1000]
                    if len(content_text) > 50:
                        results.append(TrainingExample(
                            instruction=f"Explain: {current_header}",
                            response=content_text,
                            source="pytorch_docs"
                        ))
                current_header = line.strip()
                current_content = []
            elif current_header:
                current_content.append(line)
        
        return results
    
    def add_manual_example(self, instruction: str, response: str, source: str = "manual"):
        """Add a manually created training example."""
        self.examples.append(TrainingExample(
            instruction=instruction,
            response=response,
            source=source
        ))
    
    def save_jsonl(self, filename: str = "training.jsonl") -> str:
        """Save examples as JSONL for fine-tuning."""
        filepath = os.path.join(self.OUTPUT_DIR, filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            for ex in self.examples:
                record = {
                    "instruction": ex.instruction,
                    "output": ex.response,
                    "source": ex.source
                }
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
        
        logger.info(f"Saved {len(self.examples)} examples to {filepath}")
        return filepath
    
    def get_stats(self) -> Dict:
        """Get dataset statistics."""
        sources = {}
        for ex in self.examples:
            sources[ex.source] = sources.get(ex.source, 0) + 1
        
        return {
            "total_examples": len(self.examples),
            "sources": sources,
            "avg_instruction_len": sum(len(e.instruction) for e in self.examples) / max(len(self.examples), 1),
            "avg_response_len": sum(len(e.response) for e in self.examples) / max(len(self.examples), 1)
        }


# PyTorch documentation URLs
PYTORCH_DOCS = [
    "https://pytorch.org/docs/stable/torch.html",
    "https://pytorch.org/docs/stable/nn.html",
    "https://pytorch.org/docs/stable/optim.html",
    "https://pytorch.org/docs/stable/autograd.html",
    "https://pytorch.org/docs/stable/tensor_attributes.html",
    "https://pytorch.org/docs/stable/tensors.html",
    "https://pytorch.org/tutorials/beginner/basics/intro.html",
    "https://pytorch.org/tutorials/beginner/basics/tensorqs_tutorial.html",
    "https://pytorch.org/tutorials/beginner/basics/buildmodel_tutorial.html",
    "https://pytorch.org/tutorials/beginner/basics/optimization_tutorial.html",
]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 60)
    print("   PyTorch Documentation Training Pipeline")
    print("=" * 60)
    
    pipeline = DocTrainingPipeline()
    
    print(f"\n📚 Scraping {len(PYTORCH_DOCS)} PyTorch documentation pages...")
    
    for url in PYTORCH_DOCS:
        print(f"\n🔗 {url}")
        pipeline.scrape_and_process([url])
    
    # Add some manual high-quality examples
    pipeline.add_manual_example(
        instruction="Create a simple neural network in PyTorch",
        response="""```python
import torch
import torch.nn as nn

class SimpleNet(nn.Module):
    def __init__(self, input_size, hidden_size, output_size):
        super(SimpleNet, self).__init__()
        self.fc1 = nn.Linear(input_size, hidden_size)
        self.relu = nn.ReLU()
        self.fc2 = nn.Linear(hidden_size, output_size)
    
    def forward(self, x):
        x = self.fc1(x)
        x = self.relu(x)
        x = self.fc2(x)
        return x

# Usage
model = SimpleNet(784, 128, 10)
```""",
        source="manual"
    )
    
    pipeline.add_manual_example(
        instruction="How to train a model in PyTorch",
        response="""```python
import torch
import torch.nn as nn
import torch.optim as optim

# Define model, loss, optimizer
model = YourModel()
criterion = nn.CrossEntropyLoss()
optimizer = optim.Adam(model.parameters(), lr=0.001)

# Training loop
for epoch in range(num_epochs):
    for batch_x, batch_y in dataloader:
        # Forward pass
        outputs = model(batch_x)
        loss = criterion(outputs, batch_y)
        
        # Backward pass
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
    
    print(f'Epoch {epoch+1}, Loss: {loss.item():.4f}')
```""",
        source="manual"
    )
    
    # Save dataset
    print("\n" + "=" * 60)
    filepath = pipeline.save_jsonl("pytorch_training.jsonl")
    
    stats = pipeline.get_stats()
    print(f"\n📊 Dataset Statistics:")
    print(f"   Total examples: {stats['total_examples']}")
    print(f"   Avg instruction length: {stats['avg_instruction_len']:.0f} chars")
    print(f"   Avg response length: {stats['avg_response_len']:.0f} chars")
    print(f"   Sources: {stats['sources']}")
    
    print(f"\n✅ Saved to: {filepath}")
