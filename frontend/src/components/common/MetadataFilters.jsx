import { Button, Modal } from "@mui/material";
import { useState } from "react";

export const MetadataFilters = ({ disabled }) => {
    const [modalOpen, setModalOpen] = useState(false);

    return <>
        <Button
            disabled = {disabled}
            onClick = {() => setModalOpen(true)}
        >
            Metadata Filters
        </Button>
    </>
}