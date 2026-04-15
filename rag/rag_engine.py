import re
from difflib import get_close_matches


class RAGEngine:
    def __init__(self, embedding_model, vector_store, llm_client, query_executor=None):
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.llm = llm_client
        self.executor = query_executor

    def run(self, query, k=10, history=None):
        effective_query = self._normalize_query_with_fuzzy_item(query)
        normalized_query = effective_query.lower()

        if self.executor and self._looks_structured_query(normalized_query):
            structured = self._try_structured_simple(effective_query)
            if structured:
                return structured

        filter_type = None

        if any(w in normalized_query for w in ["discount", "coupon"]):
            filter_type = "discount"
        elif any(w in normalized_query for w in ["price", "cost", "how much"]):
            filter_type = "item"
        elif "calorie" in normalized_query:
            filter_type = "nutrition"

        query_embedding = self.embedding_model.embed_query(normalized_query)

        results = self.vector_store.query(
            query_embedding,
            n_results=k,
            where={"type": filter_type} if filter_type else None
        )

        documents = results.get("documents", [[]])[0]

        if not documents:
            results = self.vector_store.query(
                query_embedding,
                n_results=k
            )
            documents = results.get("documents", [[]])[0]

        if (not documents or all(not d.strip() for d in documents)) and self.executor:
            structured = self._try_structured_simple(query)
            if structured:
                return structured

        context = "\n\n".join(documents)

        prompt = self._build_prompt(context, effective_query, history)

        response = self.llm.generate(prompt)

        return self._clean_response(response)

    def _normalize_query_with_fuzzy_item(self, query):
        if not self.executor or not getattr(self.executor, "parser", None):
            return query

        # If an exact item already appears in the query, keep it unchanged.
        if self._find_item_in_query(query.lower()):
            return query

        candidate = self._extract_freeform_item_candidate(query)
        if not candidate:
            return query

        matched = self._fuzzy_item_name(candidate)
        if not matched:
            return query

        return f"{query} (item: {matched})"

    def _extract_freeform_item_candidate(self, query):
        q = query.lower().replace("’", "'")

        patterns = [
            "tell me about ",
            "details about ",
            "information about ",
            "info about ",
            "what's in ",
            "what is in ",
            "what is ",
            "describe ",
        ]

        for pattern in patterns:
            if pattern in q:
                q = q.split(pattern, 1)[1]
                break
        else:
            return None

        q = q.strip().rstrip("?.!")
        for prefix in ["the ", "a ", "an "]:
            if q.startswith(prefix):
                q = q[len(prefix):]

        return q.strip() or None

    def _fuzzy_item_name(self, candidate):
        if not self.executor or not getattr(self.executor, "parser", None):
            return None

        normalized = re.sub(r"\s+", " ", (candidate or "").lower().strip())
        if not normalized:
            return None

        names = list(self.executor.parser.items_by_name.keys())
        if normalized in names:
            return normalized

        match = get_close_matches(normalized, names, n=1, cutoff=0.65)
        if match:
            return match[0]

        return None

    def _clean_response(self, response):
        lines = [line.strip() for line in response.splitlines()]
        lines = [line for line in lines if line]
        return "\n".join(lines).strip()

    def _looks_structured_query(self, normalized_query):
        structured_terms = [
            "price",
            "cost",
            "how much",
            "calorie",
            "coupon",
            "code",
            "active discount",
            "discount today",
            "today",
            "channel",
        ]
        return any(term in normalized_query for term in structured_terms)

    def _try_structured_simple(self, query):
        if not self.executor:
            return None

        q = query.lower()

        if "channel" in q and any(w in q for w in ["price", "cost", "how much"]):
            return "I only have one menu snapshot and cannot compare prices across channels."

        # PRICE
        if any(w in q for w in ["price", "cost", "how much"]):
            item = self._find_item_in_query(q) or self._extract_item_name(query)
            size = self._extract_size(query)

            if item:
                result = self.executor.execute({
                    "intent": "item_price",
                    "item_name": item,
                    "size": size,
                    "category": None,
                })
                if result:
                    return result
                return f"I couldn't find '{item}'. Please use the exact menu item name."

            if "smoothie" in q:
                examples = self._get_category_examples("smoothies")
                if examples:
                    size_hint = f" with size '{size}'" if size else ""
                    return (
                        f"Please specify the smoothie name{size_hint}. "
                        f"Examples: {', '.join(examples)}."
                    )

            return "Please specify the exact menu item name for a price lookup."

        # CALORIES
        if "calorie" in q:
            item = self._find_item_in_query(q) or self._extract_item_name(query)
            if item:
                result = self.executor.execute({
                    "intent": "item_nutrition",
                    "item_name": item,
                    "size": None,
                    "category": None,
                })
                if result:
                    return result
                return f"I couldn't find nutrition data for '{item}'."

            return "Please specify the exact menu item name for a calorie lookup."

        # COUPONS
        if "coupon" in q or "code" in q:
            return self.executor.execute({
                "intent": "discount_coupons",
                "item_name": None,
                "size": None,
                "category": None,
            })

        # ACTIVE DISCOUNTS
        if "today" in q or "active discount" in q:
            return self.executor.execute({
                "intent": "discount_active",
                "item_name": None,
                "size": None,
                "category": None,
            })

        return None

    def _extract_item_name(self, query):
        q = query.lower().replace("’", "'")

        patterns = [
            "how many calories does the ",
            "how many calories does ",
            "how many calories in ",
            "what's the price of ",
            "whats the price of ",
            "what's the cost of ",
            "whats the cost of ",
            "what is the price of ",
            "how much is ",
            "how much for ",
            "price of ",
            "cost of ",
        ]

        for pattern in patterns:
            if pattern in q:
                q = q.replace(pattern, "", 1)
                break

        q = q.replace("?", " ").replace("-", " ")

        tokens = [t for t in re.split(r"\s+", q.strip()) if t]

        stopwords = {
            "what",
            "what's",
            "whats",
            "is",
            "does",
            "have",
            "the",
            "a",
            "an",
            "of",
            "in",
            "for",
            "price",
            "cost",
            "calorie",
            "calories",
            "many",
            "much",
            "how",
        }

        sizes = {"small", "medium", "large", "sm", "md", "lg"}
        tokens = [t for t in tokens if t not in stopwords and t not in sizes]

        if tokens and tokens[-1] in {"smoothie", "salad", "wrap", "toast", "sandwich"}:
            tokens = tokens[:-1]

        return " ".join(tokens).strip()

    def _extract_size(self, query):
        q = query.lower()
        for size in ["small", "medium", "large", "sm", "md", "lg"]:
            if size in q:
                return size
        return None

    def _find_item_in_query(self, normalized_query):
        if not self.executor or not getattr(self.executor, "parser", None):
            return None

        names = sorted(self.executor.parser.items_by_name.keys(), key=len, reverse=True)
        for name in names:
            if name and name in normalized_query:
                return name
        return None

    def _get_category_examples(self, category_key, max_items=5):
        if not self.executor or not getattr(self.executor, "parser", None):
            return []

        parser = self.executor.parser
        keys = parser.items_by_category.get(category_key, [])

        examples = []
        seen = set()
        for key in keys:
            item = parser.items_by_name.get(key)
            if not item:
                continue
            name = item.get("name")
            if not name or name in seen:
                continue
            seen.add(name)
            examples.append(name)
            if len(examples) >= max_items:
                break

        return examples

    def _build_prompt(self, context, query, history=None):
        history_text = ""

        if history:
            for turn in history[-3:]:
                history_text += f"User: {turn['user']}\n"
                history_text += f"Assistant: {turn['assistant']}\n"

        return f"""
You are a friendly menu assistant.

Answer naturally, clearly, and concisely.
Paraphrase context into natural language instead of copying chunk text verbatim.
Do not output raw chunk labels like "Entity:", "Category:", or "Discount:" unless asked.
If any price is 0.00 state that it's probably a data base issue 
and suggest checking with staff.

Use the provided menu information as your main source.
Take typos and pluralization into account, 
but do not invent new facts like ingredients that are not in the menu.

If multiple items match the question, list ALL of them.

When answering about discounts:
- Treat discounts as independent entities.
- Do not associate discounts with items unless explicitly stated.
- If asked about coupons, include ALL discounts that explicitly 
say they REQUIRE a coupon code but do not specify the required coupon code.

Only use facts explicitly present in the provided menu information.

If information is partially available, use what is present.

If the information is not available at all, say so briefly and suggest checking
with staff.

Do not infer ingredients, protein content, dietary labels, channel-level pricing,
or ranking answers (like cheapest item) unless they are explicitly present.

Keep the tone friendly and direct. Avoid unnecessary explanations. 
Do not say according to the menu, just provide the answer. 

Conversation:
{history_text}

Menu information:
{context}

Question: {query}
Answer:
""".strip()