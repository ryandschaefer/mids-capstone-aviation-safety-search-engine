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