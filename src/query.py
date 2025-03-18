from dotenv import load_dotenv
from .entity import MovieEntities
load_dotenv()

class CypherQueryGenerator:
    def __init__(self):
        pass
    
    def generate_query_manually(self, entities: MovieEntities) -> str:
        # Handle similarity search first
        if entities.movie and len(entities.movie) > 0:
            # If both movies and genres are provided, use a combined approach
            if entities.genre and len(entities.genre) > 0:
                return self._combined_similarity_genre_query(entities)
            # Handle similarity search only
            return self._similarity_query(entities)
            
        # Standard filtering query
        return self._standard_filter_query(entities)

    def _similarity_query(self, entities: MovieEntities) -> str:
        """Handle 'movies like X' queries with similarity scoring"""
        cleaned_movie = [x.lower() for x in entities.movie]
        query_lines = [
            "MATCH (ref:Movie)",
            f"WHERE ANY(movie IN {cleaned_movie} WHERE toLower(ref.title) CONTAINS toLower(movie))",
            "WITH COLLECT(DISTINCT ref) AS refs",
            "UNWIND refs AS ref",
            "OPTIONAL MATCH (ref)-[:DIRECTED_BY]->(d:Director)",
            "OPTIONAL MATCH (ref)-[:ACTED_IN]->(a:Actor)",
            "OPTIONAL MATCH (ref)-[:HAS_GENRE]->(g:Genre)",
            "WITH refs,",
            "COLLECT(DISTINCT d) AS all_directors,",
            "COLLECT(DISTINCT a) AS all_actors,",
            "COLLECT(DISTINCT g) AS all_genres",
            "MATCH (m:Movie)",
            "WHERE NOT m IN refs",
            "OPTIONAL MATCH (m)-[:DIRECTED_BY]->(md:Director) WHERE md IN all_directors",
            "OPTIONAL MATCH (m)-[:ACTED_IN]->(ma:Actor) WHERE ma IN all_actors",
            "OPTIONAL MATCH (m)-[:HAS_GENRE]->(mg:Genre) WHERE mg IN all_genres"
        ]

        # Add additional filters
        filter_lines, params = self._build_filters(entities)
        query_lines += filter_lines

        # Add scoring and final return
        query_lines += [
            "WITH m,",
            "COUNT(DISTINCT md) * 2 AS director_score,",
            "COUNT(DISTINCT ma) AS actor_score,",
            "COUNT(DISTINCT mg) * 0.5 AS genre_score",
            # "director_score + actor_score + genre_score AS similarity_score",
            "ORDER BY (director_score + actor_score + genre_score) DESC, m.popularity DESC",
            # "ORDER BY similarity_score DESC, m.popularity DESC",
            "RETURN m.title AS title",
            "LIMIT 10"
        ]
        
        return "\n".join(query_lines)

    def _standard_filter_query(self, entities: MovieEntities) -> str:
        """Handle standard filtering without similarity"""
        query_lines = ["MATCH (m:Movie)"]
        where_conditions = []
        
        # Genre filtering
        if entities.genre:
            genres = [g.lower() for g in entities.genre]
            if entities.genres_union:
                # OR condition: any of the genres
                query_lines.append("MATCH (m)-[:HAS_GENRE]->(g:Genre)")
                where_conditions.append(
                    f"toLower(g.name) IN {genres}"
                )
            else:
                # AND condition: all genres must exist
                query_lines.append("MATCH (m)-[:HAS_GENRE]->(g:Genre)")
                where_conditions.append(
                    f"SIZE([genre IN {genres} WHERE (m)-[:HAS_GENRE]->(:Genre {{name: genre}}) | 1]) = SIZE({genres})"
                )

        # Year filtering
        if entities.year_start or entities.year_end:
            query_lines.append("MATCH (m)-[:RELEASED_IN]->(y:Year)")
            if entities.year_start:
                where_conditions.append(f"y.year >= {entities.year_start}")
            if entities.year_end:
                where_conditions.append(f"y.year <= {entities.year_end}")

        # Director filtering
        if entities.director:
            query_lines.append("MATCH (m)-[:DIRECTED_BY]->(d:Director)")
            dir_conditions = [f"toLower(d.name) CONTAINS '{d.lower()}'" for d in entities.director]
            where_conditions.append(f"({' OR '.join(dir_conditions)})")

        # Actor filtering
        if entities.actor:
            if entities.actors_union:
                query_lines.append("MATCH (m)-[:ACTED_IN]->(a:Actor)")
                actor_conds = [f"toLower(a.name) CONTAINS '{a.lower()}'" for a in entities.actor]
                where_conditions.append(f"({' OR '.join(actor_conds)})")
            else:
                for i, actor in enumerate(entities.actor):
                    query_lines.append(f"MATCH (m)-[:ACTED_IN]->(a{i}:Actor)")
                    where_conditions.append(f"toLower(a{i}.name) CONTAINS '{actor.lower()}'")

        # Build final query
        if where_conditions:
            query_lines.append(f"WHERE {' AND '.join(where_conditions)}")
            
        query_lines.append("RETURN DISTINCT m.title AS title")
        query_lines.append("LIMIT 10")
        
        return "\n".join(query_lines)

    def _combined_similarity_genre_query(self, entities: MovieEntities) -> str:
        """Handle queries with both 'movies like X' and specific genre requirements"""
        cleaned_movie = [x.lower() for x in entities.movie]
        query_lines = [
            "MATCH (ref:Movie)",
            f"WHERE ANY(movie IN {cleaned_movie} WHERE toLower(ref.title) CONTAINS toLower(movie))",
            "WITH COLLECT(DISTINCT ref) AS refs",
            "UNWIND refs AS ref",
            "OPTIONAL MATCH (ref)-[:DIRECTED_BY]->(d:Director)",
            "OPTIONAL MATCH (ref)-[:ACTED_IN]->(a:Actor)",
            "OPTIONAL MATCH (ref)-[:HAS_GENRE]->(g:Genre)",
            "WITH refs,",
            "COLLECT(DISTINCT d) AS all_directors,",
            "COLLECT(DISTINCT a) AS all_actors,",
            "COLLECT(DISTINCT g) AS all_genres",
            "MATCH (m:Movie)",
            "WHERE NOT m IN refs"
        ]

        # Add strict genre filtering for the required genres
        genres = [g.lower() for g in entities.genre]
        if entities.genres_union:
            # OR condition: match any of the requested genres
            query_lines.append("WITH m, all_directors, all_actors, all_genres")
            query_lines.append("MATCH (m)-[:HAS_GENRE]->(required_genre:Genre)")
            query_lines.append(f"WHERE toLower(required_genre.name) IN {genres}")
        else:
            # AND condition: all requested genres must be present
            query_lines.append("WITH m, all_directors, all_actors, all_genres")
            query_lines.append(f"WHERE SIZE([genre IN {genres} WHERE (m)-[:HAS_GENRE]->(:Genre {{name: genre}}) | 1]) = SIZE({genres})")

        # Continue with similarity matching
        query_lines += [
            "WITH m, all_directors, all_actors, all_genres",
            "OPTIONAL MATCH (m)-[:DIRECTED_BY]->(md:Director) WHERE md IN all_directors",
            "OPTIONAL MATCH (m)-[:ACTED_IN]->(ma:Actor) WHERE ma IN all_actors",
            "OPTIONAL MATCH (m)-[:HAS_GENRE]->(mg:Genre) WHERE mg IN all_genres"
        ]

        # Add additional filters (year, director, actor)
        filter_lines, params = self._build_filters(entities, skip_genre=True)
        query_lines += filter_lines

        # Add scoring and final return
        query_lines += [
            "WITH m,",
            "COUNT(DISTINCT md) * 2 AS director_score,",
            "COUNT(DISTINCT ma) AS actor_score,",
            "COUNT(DISTINCT mg) * 0.5 AS genre_score",
            "ORDER BY (director_score + actor_score + genre_score) DESC, m.popularity DESC",
            "RETURN m.title AS title",
            "LIMIT 10"
        ]
        
        return "\n".join(query_lines)

    def _build_filters(self, entities: MovieEntities, skip_genre=False) -> tuple:
        """Build additional filter clauses for similarity query"""
        filter_lines = []
        params = {}
        
        # Genre filters
        if entities.genre and not skip_genre:
            filter_lines.append("OPTIONAL MATCH (m)-[:HAS_GENRE]->(mg) WHERE mg IN all_genres")
            params["genres"] = [g.lower() for g in entities.genre]

        # Year filters
        if entities.year_start or entities.year_end:
            filter_lines.append("MATCH (m)-[:RELEASED_IN]->(y:Year)")
            if entities.year_start:
                filter_lines.append(f"WHERE y.year >= {entities.year_start}")
            if entities.year_end:
                filter_lines.append(f"AND y.year <= {entities.year_end}")

        # Director filters
        if entities.director:
            filter_lines.append("OPTIONAL MATCH (m)-[:DIRECTED_BY]->(md) WHERE md IN all_directors")

        # Actor filters
        if entities.actor:
            filter_lines.append("OPTIONAL MATCH (m)-[:ACTED_IN]->(ma) WHERE ma IN all_actors")

        return filter_lines, params

    