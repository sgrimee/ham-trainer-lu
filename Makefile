PY := uv run --quiet --with pymupdf python

.PHONY: all extract verify db appendix clean

all: extract appendix verify db

extract:            ## PDF -> data/questions.jsonl + data/assets/
	$(PY) extract/run.py

appendix:           ## PDF -> data/appendix/ (exam-day formula sheet)
	$(PY) extract/appendix.py

verify:             ## run every validation gate, including the round trip
	$(PY) extract/validate.py

db: verify          ## data/questions.jsonl -> build/exam.db
	python3 extract/build_db.py

clean:
	rm -rf build
