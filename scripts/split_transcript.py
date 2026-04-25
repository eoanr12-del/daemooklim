"""Split transcript.txt into readable chunks for analysis."""
import sys

input_path = sys.argv[1]
output_prefix = sys.argv[2]
chunk_size = int(sys.argv[3]) if len(sys.argv) > 3 else 4000

with open(input_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Split by spaces to get words
words = content.split()
total = len(words)
print(f"Total words: {total}")
print(f"Total chars: {len(content)}")

# Create chunks
chunk_num = 1
current_chunk = []
current_len = 0

for word in words:
    current_chunk.append(word)
    current_len += len(word) + 1
    if current_len >= chunk_size:
        chunk_text = ' '.join(current_chunk)
        out_file = f"{output_prefix}_chunk{chunk_num:02d}.txt"
        with open(out_file, 'w', encoding='utf-8') as f:
            f.write(chunk_text)
        print(f"Written chunk {chunk_num}: {out_file} ({len(chunk_text)} chars)")
        chunk_num += 1
        current_chunk = []
        current_len = 0

if current_chunk:
    chunk_text = ' '.join(current_chunk)
    out_file = f"{output_prefix}_chunk{chunk_num:02d}.txt"
    with open(out_file, 'w', encoding='utf-8') as f:
        f.write(chunk_text)
    print(f"Written chunk {chunk_num}: {out_file} ({len(chunk_text)} chars)")

print(f"Done. Total {chunk_num} chunks.")
