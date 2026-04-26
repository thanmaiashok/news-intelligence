// Neo4j initialization
// Run via: cypher-shell -u neo4j -p newspass123 < init-neo4j.cypher

CREATE CONSTRAINT article_hash IF NOT EXISTS
  FOR (a:Article) REQUIRE a.content_hash IS UNIQUE;

CREATE CONSTRAINT source_name IF NOT EXISTS
  FOR (s:Source) REQUIRE s.name IS UNIQUE;

CREATE CONSTRAINT topic_name IF NOT EXISTS
  FOR (t:Topic) REQUIRE t.name IS UNIQUE;

CREATE CONSTRAINT entity_key IF NOT EXISTS
  FOR (e:Entity) REQUIRE e.key IS UNIQUE;

CREATE INDEX article_published IF NOT EXISTS
  FOR (a:Article) ON (a.published_at);

CREATE INDEX article_sentiment IF NOT EXISTS
  FOR (a:Article) ON (a.sentiment_label);

CREATE INDEX entity_type_idx IF NOT EXISTS
  FOR (e:Entity) ON (e.type);

CREATE INDEX source_type_idx IF NOT EXISTS
  FOR (s:Source) ON (s.source_type);
