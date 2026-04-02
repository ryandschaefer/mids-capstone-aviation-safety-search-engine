import { DataTable } from "primereact/datatable";
import { Column } from "primereact/column";
import "primereact/resources/themes/lara-light-indigo/theme.css";
import { useEffect, useState } from "react";
import { Box, Button, Chip, FormControl, FormControlLabel, Grid, IconButton, InputLabel, MenuItem, Select, Switch, Tooltip, Typography } from "@mui/material";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import ThumbUpAltOutlinedIcon from "@mui/icons-material/ThumbUpAltOutlined";
import ThumbDownAltOutlinedIcon from "@mui/icons-material/ThumbDownAltOutlined";
import { MetadataFilters, SearchBar } from "../common";
import { getSearchResults, saveFeedback } from "../../api";
import { displayColumns } from "../../utils";
import { useNavigate } from "react-router-dom";
import humanizeDuration from "humanize-duration";

const normalize = (s) => (s || "").replace(/\s+/g, " ").trim();

function normalizedToOriginalPositions(text, normStart, normEnd) {
    let ni = 0;
    let inSpace = false;
    let start = -1;
    let end = -1;
    for (let i = 0; i < text.length; i++) {
        if (/\s/.test(text[i])) {
            if (!inSpace) { inSpace = true; ni++; }
        } else {
            inSpace = false;
            ni++;
        }
        if (start === -1 && ni >= normStart) start = i;
        if (end === -1 && ni >= normEnd) { end = i + 1; break; }
    }
    if (end === -1) end = text.length;
    return { start: start < 0 ? 0 : start, end };
}

function escapeRe(s) {
    return s.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

function highlightQueryTermsSimple(segment, query) {
    if (!segment || !query || !String(query).trim()) return segment;
    const terms = String(query).trim().split(/\s+/).filter((w) => w.length > 0);
    if (terms.length === 0) return segment;
    const re = new RegExp(`(${terms.map(escapeRe).join("|")})`, "gi");
    const parts = segment.split(re);
    return parts.map((p, i) => (i % 2 === 1 ? <mark key={i} style={{ backgroundColor: "rgba(255, 193, 7, 0.5)", padding: "0 1px" }}>{p}</mark> : p));
}

function NarrativeWithHighlightAndChunk({ narrative, snippet, query }) {
    const text = narrative == null ? "" : String(narrative);
    if (!text) return "";
    const nText = normalize(text);
    const nSnippet = (snippet && normalize(snippet)) || "";
    const idx = nSnippet ? nText.toLowerCase().indexOf(nSnippet.toLowerCase()) : -1;
    const hasChunk = idx >= 0;
    const pos = hasChunk ? normalizedToOriginalPositions(text, idx, idx + nSnippet.length) : { start: 0, end: 0 };
    const beforeChunk = text.slice(0, pos.start);
    const chunkText = hasChunk ? text.slice(pos.start, pos.end) : "";
    const afterChunk = hasChunk ? text.slice(pos.end) : text;
    return (
        <>
            {highlightQueryTermsSimple(beforeChunk, query)}
            {chunkText ? (
                <span style={{ backgroundColor: "rgba(255, 235, 59, 0.25)", fontWeight: 600 }}>
                    {highlightQueryTermsSimple(chunkText, query)}
                </span>
            ) : null}
            {highlightQueryTermsSimple(afterChunk, query)}
        </>
    );
}

const TIME_DATE_KEY = "Time_Date";
const PLACE_KEY = "Place_Locale Reference";
const ANOMALY_KEY = "Events_Anomaly";
const SEARCH_MODE_KEY = "search-mode";
const FEEDBACK_KEY = "result-feedback-v1";
const USE_QE_KEY = "use-qe";
const USE_QE_JUDGE_KEY = "use-qe-judge";

function applyClientFilters(rows, filters) {
    if (!rows || !rows.length) return [];
    let out = rows;
    const when = (filters.when_prefix || "").trim();
    const where = (filters.where_contains || "").trim();
    const anomaly = (filters.anomaly_contains || "").trim();
    if (when) {
        out = out.filter((r) => (r[TIME_DATE_KEY] != null && String(r[TIME_DATE_KEY]).startsWith(when)));
    }
    if (where) {
        const w = where.toLowerCase();
        out = out.filter((r) => (r[PLACE_KEY] != null && String(r[PLACE_KEY]).toLowerCase().includes(w)));
    }
    if (anomaly) {
        const a = anomaly.toLowerCase();
        out = out.filter((r) => {
            const val = r[ANOMALY_KEY] ?? r["Events_Anomaly Type"] ?? "";
            return String(val).toLowerCase().includes(a);
        });
    }
    return out;
}

export const Results = () => {
    const navigate = useNavigate();

    const [loading, setLoading] = useState(false);
    const [searchResults, setSearchResults] = useState([]);
    const [rawResults, setRawResults] = useState([]);
    const [allResults, setAllResults] = useState([]);
    const [totalResults, setTotalResults] = useState(-1);
    const [currentPage, setCurrentPage] = useState(0);
    const [pageLength, setPageLength] = useState(10);
    const [userQuery, setUserQuery] = useState("");
    const [searchMode, setSearchMode] = useState(localStorage.getItem(SEARCH_MODE_KEY) || "bm25");
    const [useQe, setUseQe] = useState(localStorage.getItem(USE_QE_KEY) === "true");
    const [useQeJudge, setUseQeJudge] = useState(localStorage.getItem(USE_QE_JUDGE_KEY) === "true");
    const [queryTime, setQueryTime] = useState(-1.0);
    const [queryTimeText, setQueryTimeText] = useState("");
    const [expandedQuery, setExpandedQuery] = useState("");
    const [filters, setFilters] = useState({ when_prefix: "", where_contains: "", anomaly_contains: "" });
    const [feedbackByDoc, setFeedbackByDoc] = useState(() => {
        try {
            return JSON.parse(localStorage.getItem(FEEDBACK_KEY) || "{}");
        } catch {
            return {};
        }
    });

    const onSubmit = () => {
        const query = localStorage.getItem("user-query");
        if (query) {
            setLoading(true);
            getSearchResults(query, searchMode, 50, {
                use_qe: useQe,
                use_qe_judge: useQeJudge,
            })
                .then((response) => {
                    const rows = Array.isArray(response?.data) ? response.data : [];
                    setRawResults(rows);

                    const used = Array.isArray(response?.used_queries) ? response.used_queries : [];
                    const latestUsedQuery = used.length > 0 ? String(used[used.length - 1]) : "";
                    const isExpanded =
                        latestUsedQuery &&
                        latestUsedQuery.trim().toLowerCase() !== query.trim().toLowerCase();

                    setExpandedQuery(isExpanded ? latestUsedQuery : "");

                    if (response?.times?.api_total) {
                        setQueryTime(response.times.api_total * 1000);
                    }
                })
                .finally(() => {
                    setLoading(false);
                    setUserQuery(query);
                });
        } else {
            navigate("/");
        }
    };

    useEffect(() => {
        if (rawResults.length >= 0 && !loading) {
            const filtered = applyClientFilters(rawResults, filters);
            setAllResults(filtered);
            setTotalResults(filtered.length);
            setSearchResults(filtered.slice(0, pageLength));
            setCurrentPage(0);
        }
    }, [rawResults, filters, loading]);

    const onPage = (event) => {
        const page = event.page;
        const start = page * pageLength;
        setCurrentPage(page);
        setSearchResults(allResults.slice(start, start + pageLength));
    };

    const setDocFeedback = async (docId, value, record = null) => {
        if (!docId) return;

        setFeedbackByDoc((prev) => {
            const next = { ...prev, [docId]: value };
            localStorage.setItem(FEEDBACK_KEY, JSON.stringify(next));
            return next;
        });

        const parsedChunkId = Number(record?.chunk_id);
        const chunkId = Number.isFinite(parsedChunkId) ? parsedChunkId : null;

        try {
            await saveFeedback({
                doc_id: docId,
                chunk_id: chunkId,
                feedback_value: value,
                query_text: userQuery || null,
                mode: searchMode,
                use_qe: useQe,
                use_qe_judge: useQeJudge,
            });
        } catch (err) {
            console.warn("Failed to persist feedback in SQL database", err);
        }
    };

    const getDocId = (record) => String(record.doc_id ?? record.acn_num_ACN ?? "");

    const onToggleQe = (checked) => {
        setUseQe(checked);
        localStorage.setItem(USE_QE_KEY, String(checked));
        if (!checked) {
            // Judge mode depends on query enhancement path.
            setUseQeJudge(false);
            localStorage.setItem(USE_QE_JUDGE_KEY, "false");
        }
    };

    useEffect(() => {
        onSubmit();
    }, []);

    useEffect(() => {
        setQueryTimeText(
            humanizeDuration(queryTime, { round: true, units: ["s", "ms"] })
        );
    }, [queryTime]);

    return (
        <Box sx={{ display: "flex", flexDirection: "column", textAlign: "center" }}>
            <Grid container rowSpacing={3} sx={{ mt: "5dvh" }}>
                <Grid size={1}>
                    <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap", justifyContent: "center" }}>
                        <Button onClick={() => navigate("/")}>Home</Button>
                        <Button onClick={() => navigate("/about")}>About</Button>
                    </Box>
                </Grid>

                <Grid size={8}>
                    <Box sx={{ width: "80%", alignItems: "center", ml: "10%" }}>
                        <SearchBar
                            disabled={loading}
                            onSubmit={onSubmit}
                            initQuery={userQuery}
                        />
                    </Box>
                </Grid>

                <Grid size={3}>
                    <Box sx={{ display: "flex", alignItems: "center", gap: 1, flexWrap: "wrap" }}>
                        <FormControl size="small" sx={{ minWidth: 100 }}>
                            <InputLabel>Mode</InputLabel>
                            <Select
                                value={searchMode}
                                label="Mode"
                                onChange={(e) => {
                                    const mode = e.target.value;
                                    setSearchMode(mode);
                                    localStorage.setItem(SEARCH_MODE_KEY, mode);
                                }}
                                disabled={loading}
                            >
                                <MenuItem value="bm25">BM25</MenuItem>
                                <MenuItem value="hybrid">Hybrid</MenuItem>
                                <MenuItem value="embeddings">Embeddings</MenuItem>
                            </Select>
                        </FormControl>
                        <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", mr: 1 }}>
                            <FormControlLabel
                                control={
                                    <Switch
                                        size="small"
                                        checked={useQe}
                                        onChange={(e) => onToggleQe(e.target.checked)}
                                        disabled={loading}
                                    />
                                }
                                label="LLM Query Enhancement"
                            />
                            <FormControlLabel
                                control={
                                    <Switch
                                        size="small"
                                        checked={useQeJudge}
                                        onChange={(e) => {
                                            const checked = e.target.checked;
                                            setUseQeJudge(checked);
                                            localStorage.setItem(USE_QE_JUDGE_KEY, String(checked));
                                        }}
                                        disabled={loading || !useQe}
                                    />
                                }
                                label="LLM Relevance Judge"
                            />
                        </Box>
                        <MetadataFilters
                            disabled={loading}
                            filters={filters}
                            onFiltersChange={setFilters}
                            onApply={() => {}}
                        />
                    </Box>
                </Grid>

                <Grid size={12}>
                    {loading && (
                        <Box sx={{ display: "flex", justifyContent: "center", alignItems: "center", mt: { xs: 3, sm: "50px" }, width: "100%" }}>
                            <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "60vh" }}>
                                <div className="spinner-border" style={{ width: "5rem", height: "5rem" }} role="status">
                                    <span className="sr-only">Loading</span>
                                </div>
                            </div>
                        </Box>
                    )}

                    {!loading && (
                        <Box>
                            <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 1, mb: 1 }}>
                                <Box sx={{ display: "flex", flexDirection: "column", alignItems: "flex-start", gap: 0.5 }}>
                                    <Typography variant="body1">
                                        {totalResults >= 0
                                            ? totalResults === 0
                                                ? `No results for "${userQuery}". Try different keywords or clear filters.`
                                                : `${totalResults} result${totalResults !== 1 ? "s" : ""} for "${userQuery}" in ${queryTimeText}`
                                            : ""}
                                    </Typography>
                                    {expandedQuery ? (
                                        <Typography variant="body2" color="text.secondary">
                                            Expanded query used: "{expandedQuery}"
                                        </Typography>
                                    ) : null}
                                    <Box sx={{ display: "flex", gap: 0.75, flexWrap: "wrap" }}>
                                        <Chip size="small" label={`Mode: ${searchMode.toUpperCase()}`} />
                                        <Chip size="small" color={useQe ? "primary" : "default"} label={`Search Path: ${useQe ? "LLM Enhanced" : "Fast Baseline"}`} />
                                        <Chip size="small" color={useQe ? "primary" : "default"} label={`LLM QE: ${useQe ? "On" : "Off"}`} />
                                        <Chip size="small" color={useQeJudge ? "primary" : "default"} label={`LLM Judge: ${useQeJudge ? "On" : "Off"}`} />
                                    </Box>
                                </Box>
                                {allResults.length > 0 && (
                                    <Button
                                        size="small"
                                        variant="outlined"
                                        startIcon={<FileDownloadIcon />}
                                        onClick={() => {
                                            const headers = displayColumns.map((c) => c.name);
                                            const escape = (v) => {
                                                const s = v == null ? "" : String(v);
                                                return s.includes(",") || s.includes('"') || s.includes("\n") ? `"${s.replace(/"/g, '""')}"` : s;
                                            };
                                            const rows = allResults.map((r) => displayColumns.map((c) => escape(r[c.id])).join(","));
                                            const csv = [headers.join(","), ...rows].join("\n");
                                            const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
                                            const url = URL.createObjectURL(blob);
                                            const a = document.createElement("a");
                                            a.href = url;
                                            a.download = `asrs-results-${userQuery.replace(/\s+/g, "-").slice(0, 30)}.csv`;
                                            a.click();
                                            URL.revokeObjectURL(url);
                                        }}
                                    >
                                        Export CSV
                                    </Button>
                                )}
                            </Box>
                            <DataTable
                                value={searchResults}
                                scrollable
                                showBoxlines
                                stripedRows
                                style={{ width: "100%", maxWidth: "100%" }}
                                lazy
                                paginator
                                rows={pageLength}
                                totalRecords={totalResults}
                                onPage={onPage}
                                first={currentPage * pageLength}
                                emptyMessage="No Records Found"
                                paginatorTemplate="FirstPageLink PrevPageLink PageLinks NextPageLink LastPageLink CurrentPageReport"
                                currentPageReportTemplate="Showing {first} to {last} of {totalRecords} entries"
                            >
                                {displayColumns.map((col, i) => {
                                    const id = col.id;
                                    const colName = col.name;
                                    return (
                                        <Column
                                            key={i}
                                            field={id}
                                            header={colName}
                                            style={{ minWidth: "130px", wordWrap: "break-word" }}
                                            body={(record) => (
                                                <Box
                                                    sx={{
                                                        minHeight: "60px",
                                                        maxHeight: "200px",
                                                        overflowY: "auto",
                                                        verticalAlign: "top",
                                                        pt: 0.5,
                                                        whiteSpace: "normal",
                                                        wordWrap: "break-word",
                                                        lineHeight: 1.4,
                                                        fontSize: "0.875rem",
                                                        "&::-webkit-scrollbar": { width: "6px" },
                                                        "&::-webkit-scrollbar-track": { background: "#f1f1f1", borderRadius: "3px" },
                                                        "&::-webkit-scrollbar-thumb": { background: "#c1c1c1", borderRadius: "3px" },
                                                        "&::-webkit-scrollbar-thumb:hover": { background: "#a1a1a1" },
                                                    }}
                                                >
                                                    {id === "Report 1_Narrative" ? (
                                                        <NarrativeWithHighlightAndChunk
                                                            narrative={record[id]}
                                                            snippet={record.snippet}
                                                            query={userQuery}
                                                        />
                                                    ) : (
                                                        record[id]
                                                    )}
                                                </Box>
                                            )}
                                        />
                                    );
                                })}
                                <Column
                                    key="feedback"
                                    header="Feedback"
                                    style={{ minWidth: "110px" }}
                                    body={(record) => {
                                        const docId = getDocId(record);
                                        const current = feedbackByDoc[docId];
                                        return (
                                            <Box sx={{ display: "flex", gap: 0.5, justifyContent: "center" }}>
                                                <Tooltip title="Relevant">
                                                    <IconButton
                                                        size="small"
                                                        color={current === "up" ? "primary" : "default"}
                                                        onClick={() => setDocFeedback(docId, "up", record)}
                                                    >
                                                        <ThumbUpAltOutlinedIcon fontSize="small" />
                                                    </IconButton>
                                                </Tooltip>
                                                <Tooltip title="Not relevant">
                                                    <IconButton
                                                        size="small"
                                                        color={current === "down" ? "error" : "default"}
                                                        onClick={() => setDocFeedback(docId, "down", record)}
                                                    >
                                                        <ThumbDownAltOutlinedIcon fontSize="small" />
                                                    </IconButton>
                                                </Tooltip>
                                            </Box>
                                        );
                                    }}
                                />
                            </DataTable>
                        </Box>
                    )}
                </Grid>
            </Grid>
        </Box>
    );
};
