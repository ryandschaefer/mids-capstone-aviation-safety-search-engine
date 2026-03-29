import { BASE_ENDPOINT } from "./utils";
import axios from "axios";

const SEARCH_ENDPOINT = `${BASE_ENDPOINT}/search`;

export const getTestData = async () => {
    const res = await axios.get(`${SEARCH_ENDPOINT}/test`);
    if (res.status !== 200) {
        console.error(`API request failed with status ${res.status}`);
        throw new Error(res.statusText);
    }
    return res.data;
};

/**
 * Call Ryan's POST /search (main_driver). Returns the cache key for search result.
 * @param {string} query - Search query
 * @param {string} mode - "bm25" | "embeddings" | "hybrid"
 * @param {number} top_k - Max results to return (default 50)
 * @param {{use_qe?: boolean, use_qe_judge?: boolean}} options - Optional LLM enhancements
 */
export const createSearch = async(
    query,
    mode = "bm25",
    top_k = 50,
    options = {}
) => {
    const payload = {
        query,
        mode,
        top_k,
        use_qe: Boolean(options.use_qe),
        use_qe_judge: Boolean(options.use_qe_judge),
    };
    const res = await axios.post(SEARCH_ENDPOINT, payload);
    if (res.status !== 200) {
        console.error(`POST ${SEARCH_ENDPOINT} failed with status ${res.status}`);
        throw new Error(res.statusText);
    }
    return {
        cache_key: res.data.cache_key ? String(res.data.cache_key) : undefined,
        cached: Boolean(res.data.cached),
        used_queries: Array.isArray(res.data?.used_queries) ? res.data.used_queries : [],
        total_results: Number(res.data.total_results),
        times: res.data?.times || {},
    };
}

/**
 * Call Ryan's GET /search/retrieve (main_driver). Returns the results array for the UI.
 * @param {string} query - Search query
 * @param {number} page - Page of results
 * @param {number} top_k - Results to return per page
 */
export const getSearchResults = async (
    cache_key, page = 1, page_length = 10
) => {
    const payload = {
        params: {
            cache_key, page, page_length
        }
    };
    const res = await axios.get(`${SEARCH_ENDPOINT}/retrieve`, payload);
    if (res.status !== 200) {
        console.error(`POST ${SEARCH_ENDPOINT} failed with status ${res.status}`);
        throw new Error(res.statusText);
    }
    return {
        data: Array.isArray(res.data) ? res.data : []
    };
};