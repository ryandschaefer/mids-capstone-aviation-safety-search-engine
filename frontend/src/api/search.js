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
 * Call Ryan's POST /search (main_driver). Returns the results array for the UI.
 * @param {string} query - Search query
 * @param {string} mode - "bm25" | "embeddings" | "hybrid"
 * @param {number} top_k - Max results to return (default 50)
 * @param {{use_qe?: boolean, use_qe_judge?: boolean}} options - Optional LLM enhancements
 */
export const getSearchResults = async (
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
        data: Array.isArray(res.data?.data) ? res.data.data : [],
        used_queries: Array.isArray(res.data?.used_queries) ? res.data.used_queries : [],
        times: res.data?.times || {},
    };
};

/** @deprecated use getSearchResults */
export const startSearch = async (
    query,
    mode = "bm25",
    options = {}
) => {
    const payload = {
        query,
        mode,
        top_k: 50,
        use_qe: Boolean(options.use_qe),
        use_qe_judge: Boolean(options.use_qe_judge),
    };
    const res = await axios.post(SEARCH_ENDPOINT, payload);
    if (res.status !== 200) throw new Error(res.statusText);
    return res.data;
};