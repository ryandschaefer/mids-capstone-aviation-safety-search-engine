import { BASE_ENDPOINT } from "./utils";
import axios from "axios";

const GROUP_ENDPOINT = `${ BASE_ENDPOINT }/data`;

export const getTestData = async() => {
    const endpoint = `${ GROUP_ENDPOINT }/test`;
    // Send API call
    const res = await axios.get(endpoint);

    // Handle error
    if (res.status !== 200) {
        console.error(`API request "GET ${ endpoint }" failed with status code ${ res.status }`);
        throw new Error(res.statusText);
    }

    return res.data;
}

/**
 * @param {string} query - Search query
 * @param {{ when_prefix?: string, where_contains?: string, anomaly_contains?: string }} filters - Optional metadata filters
 */
export const getBM25Data = async (query, filters = {}) => {
    const endpoint = `${GROUP_ENDPOINT}/bm25`;
    const params = { query };
    if (filters.when_prefix) params.when_prefix = filters.when_prefix;
    if (filters.where_contains) params.where_contains = filters.where_contains;
    if (filters.anomaly_contains) params.anomaly_contains = filters.anomaly_contains;

    const res = await axios.get(endpoint, { params });

    if (res.status !== 200) {
        console.error(`API request "GET ${endpoint}" failed with status code ${res.status}`);
        throw new Error(res.statusText);
    }

    return res.data;
};

/**
 * Submit relevance feedback (human-in-the-loop).
 * @param {string} query_text - Search query
 * @param {string} doc_id - Document/report ID (e.g. acn_num_ACN)
 * @param {boolean} relevant - True if result was relevant
 */
export const submitFeedback = async (query_text, doc_id, relevant) => {
    const endpoint = `${GROUP_ENDPOINT}/feedback`;
    const res = await axios.post(endpoint, { query_text, doc_id, relevant });
    if (res.status !== 200) {
        console.error(`POST ${endpoint} failed with status ${res.status}`);
        throw new Error(res.statusText);
    }
    return res.data;
};