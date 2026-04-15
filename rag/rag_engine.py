class RAGEngine:
    def __init__(self, embedding_model, vector_store, llm_client, query_executor=None):
        self.embedding_model = embedding_model
        self.vector_store = vector_store
        self.llm = llm_client
        self.executor = query_executor

    def run(self, query, k=10, history=None):
        normalized_query = query.lower()

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

        prompt = self._build_prompt(context, query, history)

        response = self.llm.generate(prompt)

        return response.strip()

    def _try_structured_simple(self, query):
        q = query.lower()

        # PRICE
        if any(w in q for w in ["price", "cost", "how much"]):
            item = self._extract_item_name(query)
            size = self._extract_size(query)

            if item:
                return self.executor.execute({
                    "intent": "item_price",
                    "item_name": item,
                    "size": size,
                    "category": None,
                })

        # CALORIES
        if "calorie" in q:
            item = self._extract_item_name(query)
            if item:
                return self.executor.execute({
                    "intent": "item_nutrition",
                    "item_name": item,
                    "size": None,
                    "category": None,
                })

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
        q = query.lower()

        patterns = [
            "how many calories does the ",
            "how many calories in ",
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

        for article in ["the ", "a "]:
            if q.startswith(article):
                q = q[len(article):]

        for size in ["small", "medium", "large", "sm", "md", "lg"]:
            q = q.replace(f"{size} ", "")

        for item_type in ["smoothie", "salad", "wrap", "toast", "sandwich"]:
            if q.endswith(f" {item_type}"):
                q = q[:-len(item_type)-1]

        return q.strip().rstrip("?")

    def _extract_size(self, query):
        q = query.lower()
        for size in ["small", "medium", "large", "sm", "md", "lg"]:
            if size in q:
                return size
        return None

    def _build_prompt(self, context, query, history=None):
        history_text = ""

        if history:
            for turn in history[-3:]:
                history_text += f"User: {turn['user']}\n"
                history_text += f"Assistant: {turn['assistant']}\n"

        return f"""
You are a friendly menu assistant.

Answer naturally, clearly, and concisely.

Use the provided menu information as your main source.
Take typos and pluralization into account, 
but do not invent new facts like ingredients that are not in the menu.

If multiple items match the question, list ALL of them.

When answering about discounts:
- Treat discounts as independent entities.
- Do not associate discounts with items unless explicitly stated.
- If asked about coupons, include ALL discounts that explicitly 
say they REQUIRE a coupon code but do not specify the required coupon code.

If information is partially available, use what is present.

If the information is not available at all, say so briefly.

Keep the tone friendly and direct. Avoid unnecessary explanations. 
Do not say according to the menu, just provide the answer. 

Conversation:
{history_text}

Menu information:
{context}

Question: {query}
Answer:
""".strip()