import React, { useState, useEffect } from "react";

// Utility to extract template parts like {word}, {user}, etc.
function extractTemplateParts(str: string): string[] {
  const regex = /{(\w+)}/g;
  const parts = new Set<string>();
  let match;
  while ((match = regex.exec(str))) {
    parts.add(match[1]);
  }
  return Array.from(parts);
}

const LanguageFormField = ({
  field,
  value,
  onChange,
  errors,
  templateArgs = [],
}: {
  field: string;
  value: string;
  onChange: (value: string, errors: string[]) => void;
  errors: string[];
  templateArgs?: string[];
}) => {
  // Ensure value is always a string to avoid undefined errors
  const safeValue = typeof value === "string" ? value : "";

  const [localValue, setLocalValue] = useState(safeValue);

  // Only show the last part of the field key as label
  const label = field.split(".").slice(-1)[0];

  // Use templateArgs prop if provided, otherwise extract from value
  const templateParts =
    templateArgs.length > 0 ? templateArgs : extractTemplateParts(value);

  // Validate required template parts, forbidden parts, and min length
  const validate = (val: string) => {
    const missing = templateParts.filter((p) => !val.includes(`{${p}}`));
    // Find all {something} in val
    const regex = /{(\w+)}/g;
    const found = new Set<string>();
    let match;
    while ((match = regex.exec(val))) {
      found.add(match[1]);
    }
    const forbidden = Array.from(found).filter((p) => !templateParts.includes(p));
    let errorList: string[] = [];
    if (val.length < 1) errorList.push("Field must be at least 1 character long");
    if (missing.length > 0) errorList.push(`Missing: ${missing.join(", ")}`);
    if (forbidden.length > 0) errorList.push(`Forbidden: ${forbidden.join(", ")}`);
    onChange(val, errorList);
  };

  // Keep localValue in sync if parent changes (for editing existing)
  useEffect(() => {
    setLocalValue(typeof value === "string" ? value : "");
    // eslint-disable-next-line
  }, [value]);

  // Handle drag and drop
  const handleDrop = (e: React.DragEvent<HTMLTextAreaElement>) => {
    e.preventDefault();
    const insert = e.dataTransfer.getData("text/plain");
    const start = e.currentTarget.selectionStart;
    const end = e.currentTarget.selectionEnd;
    const newValue =
      localValue.slice(0, start) + insert + localValue.slice(end);
    setLocalValue(newValue);
    validate(newValue);
  };

  return (
    <div className="mb-4">
      <label className="block text-sm font-medium text-gray-700 mb-1">
        {label}
      </label>
      <div className="flex gap-2 mb-1">
        {templateParts.map((part) => {
          const isUsed = localValue.includes(`{${part}}`);
          return (
            <button
              type="button"
              key={part}
              draggable
              onDragStart={(e) => {
                e.dataTransfer.setData("text/plain", `{${part}}`);
              }}
              className={
                "px-2 py-1 font-mono text-xs cursor-grab transition " +
                (isUsed
                  ? "border border-gray-600 bg-gray-100 text-gray-900"
                  : "border border-blue-500 bg-blue-50 text-blue-950 hover:bg-blue-100") +
                " rounded"
              }
              title={`Drag {${part}} into the input`}
              style={{
                userSelect: "none",
                marginBottom: "2px",
                marginRight: "2px",
                opacity: isUsed ? 0.7 : 1,
                fontWeight: isUsed ? "bold" : "normal",
              }}
            >
              {"{" + part + "}"}
            </button>
          );
        })}
      </div>
      <textarea
        value={localValue}
        onChange={(e) => {
          setLocalValue(e.target.value);
          validate(e.target.value);
        }}
        onDrop={handleDrop}
        rows={2}
        className={`w-full p-2 border rounded bg-white text-blue-950 ${
          errors.length ? "border-red-500 shadow-md shadow-red-500" : "border-gray-300"
        }`}
        placeholder={
          templateParts.length
            ? `Must include: ${templateParts.map((p) => `{${p}}`).join(", ")}`
            : undefined
        }
      />
      {errors.length > 0 && (
        <p className="text-red-500 text-sm mt-1">{errors.join(", ")}</p>
      )}
    </div>
  );
};

export default LanguageFormField;