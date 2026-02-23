/**
 * Kage Scan — Konva Canvas Editor
 * Renders the manga page image with interactive text block overlays.
 * Supports drag & resize via Konva Transformer.
 */

import { useRef, useEffect, useState, useCallback } from "react";
import { Stage, Layer, Image as KonvaImage, Rect, Transformer } from "react-konva";
import useProjectStore from "../../stores/projectStore";

/**
 * Custom hook to load an image from URL into a DOM Image element.
 */
function useImage(url) {
    const [image, setImage] = useState(null);

    useEffect(() => {
        if (!url) {
            setImage(null);
            return;
        }

        const img = new window.Image();
        img.crossOrigin = "anonymous";
        img.onload = () => setImage(img);
        img.onerror = () => setImage(null);
        img.src = url;

        return () => {
            img.onload = null;
            img.onerror = null;
        };
    }, [url]);

    return image;
}

export default function Canvas() {
    const activePage = useProjectStore((s) => s.activePage);
    const selectedBlockId = useProjectStore((s) => s.selectedBlockId);
    const selectTextBlock = useProjectStore((s) => s.selectTextBlock);
    const updateTextBlock = useProjectStore((s) => s.updateTextBlock);

    const stageRef = useRef(null);
    const transformerRef = useRef(null);
    const selectedRectRef = useRef(null);
    const containerRef = useRef(null);

    const [stageSize, setStageSize] = useState({ width: 800, height: 600 });
    const [scale, setScale] = useState(1);

    // Build image URL from the page's image_path
    const imageUrl = activePage
        ? `/data/${activePage.image_path}`
        : null;

    const pageImage = useImage(imageUrl);

    // ── Fit stage to container ──────────────────────────────────
    useEffect(() => {
        const container = containerRef.current;
        if (!container) return;

        const observer = new ResizeObserver((entries) => {
            const { width, height } = entries[0].contentRect;
            setStageSize({ width, height });
        });

        observer.observe(container);
        return () => observer.disconnect();
    }, []);

    // ── Calculate scale to fit image in stage ───────────────────
    useEffect(() => {
        if (!pageImage) return;
        const scaleX = stageSize.width / pageImage.naturalWidth;
        const scaleY = stageSize.height / pageImage.naturalHeight;
        setScale(Math.min(scaleX, scaleY, 1)); // Never upscale
    }, [pageImage, stageSize]);

    // ── Attach transformer to selected rect ─────────────────────
    useEffect(() => {
        const tr = transformerRef.current;
        if (!tr) return;

        if (selectedRectRef.current) {
            tr.nodes([selectedRectRef.current]);
            tr.getLayer()?.batchDraw();
        } else {
            tr.nodes([]);
        }
    }, [selectedBlockId]);

    // ── Handlers ────────────────────────────────────────────────
    const handleStageClick = useCallback(
        (e) => {
            // Click on empty space = deselect
            if (e.target === e.target.getStage() || e.target.name() === "page-image") {
                selectTextBlock(null);
            }
        },
        [selectTextBlock]
    );

    const handleBlockClick = useCallback(
        (blockId) => {
            selectTextBlock(blockId);
        },
        [selectTextBlock]
    );

    const handleDragEnd = useCallback(
        (blockId, e) => {
            const node = e.target;
            updateTextBlock(blockId, {
                box_x: Math.round(node.x() / scale),
                box_y: Math.round(node.y() / scale),
            });
        },
        [updateTextBlock, scale]
    );

    const handleTransformEnd = useCallback(
        (blockId, e) => {
            const node = e.target;
            const scaleX = node.scaleX();
            const scaleY = node.scaleY();

            // Reset scale and apply to width/height
            node.scaleX(1);
            node.scaleY(1);

            updateTextBlock(blockId, {
                box_x: Math.round(node.x() / scale),
                box_y: Math.round(node.y() / scale),
                box_width: Math.round((node.width() * scaleX) / scale),
                box_height: Math.round((node.height() * scaleY) / scale),
            });
        },
        [updateTextBlock, scale]
    );

    const textBlocks = activePage?.text_blocks || [];

    if (!activePage) {
        return (
            <div className="flex-1 flex items-center justify-center text-neutral-600 text-sm">
                Selecione uma página para editar
            </div>
        );
    }

    return (
        <div
            ref={containerRef}
            className="flex-1 relative overflow-hidden rounded-xl bg-ink-800/50 border border-white/[0.03]"
        >
            <Stage
                ref={stageRef}
                width={stageSize.width}
                height={stageSize.height}
                onClick={handleStageClick}
                onTap={handleStageClick}
            >
                <Layer>
                    {/* Manga page image */}
                    {pageImage && (
                        <KonvaImage
                            image={pageImage}
                            x={0}
                            y={0}
                            width={pageImage.naturalWidth * scale}
                            height={pageImage.naturalHeight * scale}
                            name="page-image"
                            listening={true}
                        />
                    )}

                    {/* Text block overlays */}
                    {textBlocks.map((block) => {
                        const isSelected = block.id === selectedBlockId;

                        return (
                            <Rect
                                key={block.id}
                                ref={isSelected ? selectedRectRef : null}
                                x={block.box_x * scale}
                                y={block.box_y * scale}
                                width={block.box_width * scale}
                                height={block.box_height * scale}
                                fill={
                                    isSelected
                                        ? "rgba(243, 145, 160, 0.35)"
                                        : "rgba(243, 145, 160, 0.15)"
                                }
                                stroke={isSelected ? "#F391A0" : "rgba(243, 145, 160, 0.4)"}
                                strokeWidth={isSelected ? 2 : 1}
                                cornerRadius={4}
                                draggable
                                onClick={() => handleBlockClick(block.id)}
                                onTap={() => handleBlockClick(block.id)}
                                onDragEnd={(e) => handleDragEnd(block.id, e)}
                                onTransformEnd={(e) => handleTransformEnd(block.id, e)}
                                onMouseEnter={(e) => {
                                    e.target.getStage().container().style.cursor = "move";
                                }}
                                onMouseLeave={(e) => {
                                    e.target.getStage().container().style.cursor = "default";
                                }}
                            />
                        );
                    })}

                    {/* Transformer for resize handles */}
                    <Transformer
                        ref={transformerRef}
                        anchorFill="#F391A0"
                        anchorStroke="#FFB8C6"
                        anchorSize={8}
                        borderStroke="#F391A0"
                        borderDash={[4, 4]}
                        enabledAnchors={[
                            "top-left",
                            "top-right",
                            "bottom-left",
                            "bottom-right",
                            "middle-left",
                            "middle-right",
                        ]}
                        rotateEnabled={false}
                        boundBoxFunc={(oldBox, newBox) => {
                            // Minimum size constraint
                            if (newBox.width < 20 || newBox.height < 20) return oldBox;
                            return newBox;
                        }}
                    />
                </Layer>
            </Stage>

            {/* Zoom indicator */}
            <div className="absolute bottom-3 right-3 px-2.5 py-1 rounded-lg glass-surface text-[10px] text-neutral-500 font-mono">
                {Math.round(scale * 100)}%
            </div>
        </div>
    );
}
