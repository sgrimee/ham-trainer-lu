PY := uv run --quiet --with pymupdf python

.PHONY: all extract verify appendix clean

all: extract appendix verify

extract:            ## PDF -> data/questions.jsonl + data/assets/
	$(PY) extract/run.py

appendix:           ## PDF -> data/appendix/ (exam-day formula sheet)
	$(PY) extract/appendix.py

verify:             ## run every validation gate, including the round trip
	$(PY) extract/validate.py

clean:
	rm -rf extract/__pycache__
