import logging
from datetime import datetime
from typing import Dict, List, Optional

from neo4j import AsyncGraphDatabase, AsyncDriver

from backend.config import settings

logger = logging.getLogger(__name__)

INIT_CONSTRAINTS = [
    "CREATE CONSTRAINT article_hash IF NOT EXISTS FOR (a:Article) REQUIRE a.content_hash IS UNIQUE",
    "CREATE CONSTRAINT source_name IF NOT EXISTS FOR (s:Source) REQUIRE s.name IS UNIQUE",
    "CREATE CONSTRAINT topic_name IF NOT EXISTS FOR (t:Topic) REQUIRE t.name IS UNIQUE",
    "CREATE CONSTRAINT entity_key IF NOT EXISTS FOR (e:Entity) REQUIRE e.key IS UNIQUE",
]

INIT_INDEXES = [
    "CREATE INDEX article_published IF NOT EXISTS FOR (a:Article) ON (a.published_at)",
    "CREATE INDEX article_sentiment IF NOT EXISTS FOR (a:Article) ON (a.sentiment_label)",
    "CREATE INDEX entity_type IF NOT EXISTS FOR (e:Entity) ON (e.type)",
]


class Neo4jClient:
    def __init__(self):
        self._driver: Optional[AsyncDriver] = None

    async def connect(self):
        self._driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
            max_connection_lifetime=3600,
            max_connection_pool_size=50,
        )
        await self._init_schema()
        logger.info("Neo4j connected")

    async def _init_schema(self):
        async with self._driver.session() as session:
            for stmt in INIT_CONSTRAINTS + INIT_INDEXES:
                try:
                    await session.run(stmt)
                except Exception as e:
                    logger.debug("Neo4j schema init: %s", e)

    async def disconnect(self):
        if self._driver:
            await self._driver.close()

    async def store_article(self, article: Dict):
        """
        Creates:
          (:Article) -[:FROM_SOURCE]-> (:Source)
          (:Article) -[:TAGGED_AS]-> (:Topic)
          (:Article) -[:MENTIONS]-> (:Entity)
          (:Entity)  -[:RELATES_TO]-> (:Entity) when co-mentioned
          (:Topic)   -[:TRENDING_WITH]-> (:Topic) when co-categorized
        """
        async with self._driver.session() as session:
            await session.execute_write(self._create_article_graph, article)

    @staticmethod
    async def _create_article_graph(tx, article: Dict):
        published_at = article.get("published_at", datetime.utcnow().isoformat())
        if isinstance(published_at, datetime):
            published_at = published_at.isoformat()

        sentiment = article.get("sentiment", {})

        # Merge Article node
        await tx.run(
            """
            MERGE (a:Article {content_hash: $hash})
            ON CREATE SET
                a.url = $url,
                a.title = $title,
                a.source = $source,
                a.source_type = $source_type,
                a.published_at = $published_at,
                a.sentiment_label = $sentiment_label,
                a.sentiment_score = $sentiment_score,
                a.region = $region,
                a.created_at = datetime()
            """,
            hash=article.get("content_hash"),
            url=article.get("url", ""),
            title=article.get("title", "")[:500],
            source=article.get("source", ""),
            source_type=article.get("source_type", ""),
            published_at=published_at,
            sentiment_label=sentiment.get("label", "neutral"),
            sentiment_score=float(sentiment.get("score", 0.5)),
            region=article.get("region", "") or "",
        )

        # Source node
        await tx.run(
            """
            MERGE (s:Source {name: $source})
            ON CREATE SET s.source_type = $source_type, s.created_at = datetime()
            ON MATCH SET s.last_seen = datetime(), s.article_count = coalesce(s.article_count, 0) + 1
            WITH s
            MATCH (a:Article {content_hash: $hash})
            MERGE (a)-[:FROM_SOURCE]->(s)
            """,
            source=article.get("source", "unknown"),
            source_type=article.get("source_type", ""),
            hash=article.get("content_hash"),
        )

        # Topic / Category nodes
        categories = article.get("categories", [])
        for cat in categories:
            await tx.run(
                """
                MERGE (t:Topic {name: $name})
                ON CREATE SET t.created_at = datetime()
                ON MATCH SET t.mention_count = coalesce(t.mention_count, 0) + 1
                WITH t
                MATCH (a:Article {content_hash: $hash})
                MERGE (a)-[:TAGGED_AS]->(t)
                """,
                name=cat,
                hash=article.get("content_hash"),
            )

        # Co-category TRENDING_WITH
        if len(categories) > 1:
            for i in range(len(categories)):
                for j in range(i + 1, len(categories)):
                    await tx.run(
                        """
                        MATCH (t1:Topic {name: $t1}), (t2:Topic {name: $t2})
                        MERGE (t1)-[r:TRENDING_WITH]->(t2)
                        ON CREATE SET r.weight = 1
                        ON MATCH SET r.weight = r.weight + 1
                        """,
                        t1=categories[i],
                        t2=categories[j],
                    )

        # Entity nodes
        entities = article.get("entities", [])
        entity_keys = []
        for ent in entities:
            key = f"{ent.get('type', 'unknown')}:{ent.get('name', '')}".lower()[:200]
            entity_keys.append(key)
            await tx.run(
                """
                MERGE (e:Entity {key: $key})
                ON CREATE SET
                    e.name = $name,
                    e.type = $type,
                    e.created_at = datetime()
                ON MATCH SET
                    e.mention_count = coalesce(e.mention_count, 0) + 1
                WITH e
                MATCH (a:Article {content_hash: $hash})
                MERGE (a)-[:MENTIONS {sentiment: $sentiment}]->(e)
                """,
                key=key,
                name=ent.get("name", ""),
                type=ent.get("type", "unknown"),
                hash=article.get("content_hash"),
                sentiment=sentiment.get("label", "neutral"),
            )

        # Co-entity RELATES_TO (cap at 5x5 to avoid explosion)
        entity_keys = entity_keys[:5]
        if len(entity_keys) > 1:
            for i in range(len(entity_keys)):
                for j in range(i + 1, len(entity_keys)):
                    await tx.run(
                        """
                        MATCH (e1:Entity {key: $k1}), (e2:Entity {key: $k2})
                        MERGE (e1)-[r:RELATES_TO]->(e2)
                        ON CREATE SET r.weight = 1
                        ON MATCH SET r.weight = r.weight + 1
                        """,
                        k1=entity_keys[i],
                        k2=entity_keys[j],
                    )

    async def get_graph_subgraph(
        self,
        center: str = None,
        depth: int = 2,
        limit: int = 100,
    ) -> Dict:
        """Returns nodes + relationships for D3 graph visualization."""
        async with self._driver.session() as session:
            if center:
                result = await session.run(
                    """
                    MATCH p = (n {name: $center})-[*1..2]-(m)
                    RETURN p LIMIT $limit
                    """,
                    center=center,
                    limit=limit,
                )
            else:
                result = await session.run(
                    """
                    MATCH (a:Article)-[r]-(b)
                    RETURN a, r, b
                    ORDER BY a.published_at DESC
                    LIMIT $limit
                    """,
                    limit=limit,
                )

            nodes = {}
            links = []
            async for record in result:
                for key in record.keys():
                    val = record[key]
                    if hasattr(val, "id"):
                        node_id = str(val.id)
                        if node_id not in nodes:
                            labels = list(val.labels) if hasattr(val, "labels") else []
                            nodes[node_id] = {
                                "id": node_id,
                                "label": labels[0] if labels else "Node",
                                "properties": dict(val),
                            }
                    elif hasattr(val, "type"):
                        links.append({
                            "source": str(val.start_node.id),
                            "target": str(val.end_node.id),
                            "type": val.type,
                            "properties": dict(val),
                        })

            return {"nodes": list(nodes.values()), "links": links}

    async def get_entity_connections(self, entity_name: str) -> List[Dict]:
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (e:Entity {name: $name})-[r:RELATES_TO]-(other:Entity)
                RETURN other.name as name, other.type as type, r.weight as weight
                ORDER BY r.weight DESC
                LIMIT 20
                """,
                name=entity_name,
            )
            return [dict(r) async for r in result]

    async def get_trending_topics(self, limit: int = 10) -> List[Dict]:
        async with self._driver.session() as session:
            result = await session.run(
                """
                MATCH (t:Topic)
                RETURN t.name as name, coalesce(t.mention_count, 0) as count
                ORDER BY count DESC
                LIMIT $limit
                """,
                limit=limit,
            )
            return [dict(r) async for r in result]
