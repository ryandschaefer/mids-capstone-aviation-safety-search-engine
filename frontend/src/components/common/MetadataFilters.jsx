import {
    Box,
    Button,
    Chip,
    Divider,
    FormControl,
    InputLabel,
    Modal,
    OutlinedInput,
    Tooltip,
    Typography,
} from "@mui/material";
import { useState } from "react";

/**
 * Graduate-level metadata filters for ASRS search.
 * - Date (when): filter by event year or year-month — supports trend and recency analysis.
 * - Location (where): filter by place/locale — supports geographic and airport-specific analysis.
 * - Anomaly type: filter by Events_Anomaly — supports finding similar incident types (e.g. altitude deviation, runway incursion).
 * Filters are applied together (AND). Apply triggers a new search with current filters.
 */
export const MetadataFilters = ({ disabled, filters = {}, onFiltersChange, onApply }) => {
    const [modalOpen, setModalOpen] = useState(false);
    const [local, setLocal] = useState({
        when_prefix: filters.when_prefix ?? "",
        where_contains: filters.where_contains ?? "",
        anomaly_contains: filters.anomaly_contains ?? "",
    });

    const handleOpen = () => {
        setLocal({
            when_prefix: filters.when_prefix ?? "",
            where_contains: filters.where_contains ?? "",
            anomaly_contains: filters.anomaly_contains ?? "",
        });
        setModalOpen(true);
    };

    const handleApply = () => {
        onFiltersChange?.(local);
        setModalOpen(false);
        if (onApply) onApply();
    };

    const handleClear = () => {
        const empty = { when_prefix: "", where_contains: "", anomaly_contains: "" };
        setLocal(empty);
        onFiltersChange?.(empty);
        setModalOpen(false);
        if (onApply) onApply();
    };

    const hasActive = (filters.when_prefix || "").trim() || (filters.where_contains || "").trim() || (filters.anomaly_contains || "").trim();

    return (
        <>
            <Button disabled={disabled} onClick={handleOpen} variant="outlined">
                Metadata Filters
                {hasActive ? " (on)" : ""}
            </Button>
            <Modal open={modalOpen} onClose={() => setModalOpen(false)} aria-labelledby="metadata-filters-modal">
                <Box
                    sx={{
                        position: "absolute",
                        top: "50%",
                        left: "50%",
                        transform: "translate(-50%, -50%)",
                        width: 400,
                        maxWidth: "90vw",
                        bgcolor: "background.paper",
                        boxShadow: 24,
                        p: 3,
                        borderRadius: 2,
                    }}
                >
                    <Typography id="metadata-filters-modal" variant="h6" component="h2" gutterBottom>
                        Metadata Filters
                    </Typography>
                    <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                        Narrow results by event date, location, or anomaly type. All filters are combined (AND).
                    </Typography>

                    <Tooltip title="Filter by event date (report date). Use year (e.g. 2019) or year-month (e.g. 201906)." placement="top">
                        <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                            <InputLabel shrink>Date (year or YYYYMM)</InputLabel>
                            <OutlinedInput
                                value={local.when_prefix}
                                onChange={(e) => setLocal((p) => ({ ...p, when_prefix: e.target.value }))}
                                placeholder="e.g. 2019 or 201906"
                                label="Date (year or YYYYMM)"
                            />
                        </FormControl>
                    </Tooltip>

                    <Tooltip title="Filter by place/locale (e.g. airport code, state, or region)." placement="top">
                        <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                            <InputLabel shrink>Location</InputLabel>
                            <OutlinedInput
                                value={local.where_contains}
                                onChange={(e) => setLocal((p) => ({ ...p, where_contains: e.target.value }))}
                                placeholder="e.g. LAS, Texas, Airport"
                                label="Location"
                            />
                        </FormControl>
                    </Tooltip>

                    <Tooltip title="Filter by type of safety event (e.g. Altitude, Deviation, Runway, Incursion)." placement="top">
                        <FormControl fullWidth size="small" sx={{ mb: 2 }}>
                            <InputLabel shrink>Anomaly type</InputLabel>
                            <OutlinedInput
                                value={local.anomaly_contains}
                                onChange={(e) => setLocal((p) => ({ ...p, anomaly_contains: e.target.value }))}
                                placeholder="e.g. Altitude, Deviation, Runway"
                                label="Anomaly type"
                            />
                        </FormControl>
                    </Tooltip>

                    <Divider sx={{ my: 2 }} />

                    <Box sx={{ display: "flex", gap: 1, justifyContent: "flex-end" }}>
                        <Button onClick={handleClear} color="inherit">
                            Clear all
                        </Button>
                        <Button onClick={() => setModalOpen(false)}>Cancel</Button>
                        <Button variant="contained" onClick={handleApply}>
                            Apply
                        </Button>
                    </Box>

                    {hasActive && (
                        <Box sx={{ mt: 2 }}>
                            <Typography variant="caption" color="text.secondary">
                                Active:
                            </Typography>
                            <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 0.5 }}>
                                {filters.when_prefix && (
                                    <Chip size="small" label={`Date: ${filters.when_prefix}`} onDelete={() => onFiltersChange?.({ ...filters, when_prefix: "" })} />
                                )}
                                {filters.where_contains && (
                                    <Chip size="small" label={`Location: ${filters.where_contains}`} onDelete={() => onFiltersChange?.({ ...filters, where_contains: "" })} />
                                )}
                                {filters.anomaly_contains && (
                                    <Chip size="small" label={`Anomaly: ${filters.anomaly_contains}`} onDelete={() => onFiltersChange?.({ ...filters, anomaly_contains: "" })} />
                                )}
                            </Box>
                        </Box>
                    )}
                </Box>
            </Modal>
        </>
    );
};
