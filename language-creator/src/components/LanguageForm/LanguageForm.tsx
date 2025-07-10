import React, { useState } from "react";
import LanguageFormField from "./LanguageFormField";

// Updated structure: all sections from en.json included
const languageStructure = {
  lang_code: "",
  error: {
    value: "",
    template_args: []
  },
  no_access: {
    value: "",
    template_args: []
  },
  word: {
    no_args: {
      value: "",
      template_args: []
    },
    invalid_action: {
      value: "",
      template_args: []
    },
    list_empty: {
      value: "",
      template_args: []
    },
    list_header: {
      value: "",
      template_args: []
    },
    cleared: {
      value: "",
      template_args: []
    },
    too_short: {
      value: "",
      template_args: ["action"]
    },
    ban_banned: {
      value: "",
      template_args: ["words"]
    },
    banned_success: {
      value: "",
      template_args: ["words"]
    },
    already_banned: {
      value: "",
      template_args: ["words"]
    },
    unban_not_banned: {
      value: "",
      template_args: ["words"]
    },
    unbanned_success: {
      value: "",
      template_args: ["words"]
    },
    already_unbanned: {
      value: "",
      template_args: ["words"]
    }
  },
  mod: {
    no_args: {
      value: "",
      template_args: []
    },
    invalid_action: {
      value: "",
      template_args: []
    },
    list_empty: {
      value: "",
      template_args: []
    },
    list_header: {
      value: "",
      template_args: []
    },
    add_superadmin: {
      value: "",
      template_args: []
    },
    add_already: {
      value: "",
      template_args: []
    },
    add_success: {
      value: "",
      template_args: ["user"]
    },
    delete_superadmin: {
      value: "",
      template_args: []
    },
    delete_success: {
      value: "",
      template_args: ["user"]
    },
    reply: {
      value: "",
      template_args: []
    }
  },
  template: {
    no_args: {
      value: "",
      template_args: []
    },
    invalid_action: {
      value: "",
      template_args: []
    },
    list_empty: {
      value: "",
      template_args: []
    },
    list_header: {
      value: "",
      template_args: []
    },
    list_item: {
      value: "",
      template_args: ["template_id", "template"]
    },
    add_no_text: {
      value: "",
      template_args: []
    },
    add_success: {
      value: "",
      template_args: []
    },
    remove_no_id: {
      value: "",
      template_args: []
    },
    remove_success: {
      value: "",
      template_args: []
    },
    remove_value_error: {
      value: "",
      template_args: []
    }
  },
  messages: {
    recent: {
      value: "",
      template_args: []
    },
    recent_item: {
      value: "",
      template_args: ["user", "message"]
    },
    recent_empty: {
      value: "",
      template_args: []
    }
  },
  delete: {
    show: {
      value: "",
      template_args: ["current"]
    },
    invalid_action: {
      value: "",
      template_args: []
    },
    switch: {
      value: "",
      template_args: ["value"]
    }
  },
  locale: {
    no_args: {
      value: "",
      template_args: []
    },
    invalid_action: {
      value: "",
      template_args: []
    },
    list_empty: {
      value: "",
      template_args: []
    },
    list: {
      value: "",
      template_args: []
    },
    current_empty: {
      value: "",
      template_args: []
    },
    current: {
      value: "",
      template_args: ["locale"]
    },
    set_no_locale: {
      value: "",
      template_args: []
    },
    set_invalid_locale: {
      value: "",
      template_args: ["locale"]
    },
    set: {
      value: "",
      template_args: ["locale"]
    }
  },
  statistics: {
    format: {
      value: "",
      template_args: []
    },
    header: {
      value: "",
      template_args: ["date"]
    },
    users_header: {
      value: "",
      template_args: []
    },
    users_item: {
      value: "",
      template_args: ["id", "user", "count"]
    },
    words_header: {
      value: "",
      template_args: []
    },
    words_item: {
      value: "",
      template_args: ["id", "word", "count"]
    },
    most_banned: {
      value: "",
      template_args: ["message"]
    },
    empty: {
      value: "",
      template_args: []
    }
  },
  bot_add: {
    no_new: {
      value: "",
      template_args: []
    },
    welcome: {
      value: "",
      template_args: []
    }
  },
  help: {
    help_short: {
      header: {
        value: "",
        template_args: []
      },
      word_header: {
        value: "",
        template_args: []
      },
      word_ban: {
        value: "",
        template_args: []
      },
      word_unban: {
        value: "",
        template_args: []
      },
      word_list: {
        value: "",
        template_args: []
      },
      word_clear: {
        value: "",
        template_args: []
      },
      mod_header: {
        value: "",
        template_args: []
      },
      mod_add: {
        value: "",
        template_args: []
      },
      mod_delete: {
        value: "",
        template_args: []
      },
      mod_list: {
        value: "",
        template_args: []
      },
      template_header: {
        value: "",
        template_args: []
      },
      template_add: {
        value: "",
        template_args: []
      },
      template_delete: {
        value: "",
        template_args: []
      },
      template_list: {
        value: "",
        template_args: []
      },
      locale_header: {
        value: "",
        template_args: []
      },
      locale_list: {
        value: "",
        template_args: []
      },
      locale_current: {
        value: "",
        template_args: []
      },
      locale_set: {
        value: "",
        template_args: []
      },
      other_header: {
        value: "",
        template_args: []
      },
      other_messages: {
        value: "",
        template_args: []
      },
      other_delete: {
        value: "",
        template_args: []
      },
      other_statistics: {
        value: "",
        template_args: []
      },
      other_help: {
        value: "",
        template_args: []
      }
    },
    help_texts: {
      word: {
        none: {
          value: "",
          template_args: ["help_template"]
        },
        ban: {
          value: "",
          template_args: ["help_template", "help_ex"]
        },
        unban: {
          value: "",
          template_args: ["help_template", "help_ex"]
        },
        list: {
          value: "",
          template_args: ["help_template"]
        },
        clear: {
          value: "",
          template_args: ["help_template"]
        }
      },
      mod: {
        none: {
          value: "",
          template_args: ["help_template"]
        },
        add: {
          value: "",
          template_args: ["help_template", "help_ex"]
        },
        delete: {
          value: "",
          template_args: ["help_template", "help_ex"]
        },
        list: {
          value: "",
          template_args: ["help_template"]
        }
      },
      template: {
        none: {
          value: "",
          template_args: ["help_template"]
        },
        add: {
          value: "",
          template_args: ["help_template", "help_ex"]
        },
        delete: {
          value: "",
          template_args: ["help_template", "help_ex"]
        },
        list: {
          value: "",
          template_args: ["help_template"]
        }
      },
      locale: {
        none: {
          value: "",
          template_args: ["help_template"]
        },
        list: {
          value: "",
          template_args: ["help_template"]
        },
        current: {
          value: "",
          template_args: ["help_template"]
        },
        set: {
          value: "",
          template_args: ["help_template", "help_ex"]
        }
      },
      help: {
        none: {
          value: "",
          template_args: ["help_template", "help_ex"]
        },
        help: {
          value: "",
          template_args: []
        }
      },
      messages: {
        value: "",
        template_args: ["help_template", "help_ex"]
      },
      delete: {
        value: "",
        template_args: ["help_template", "help_ex"]
      },
      statistics: {
        value: "",
        template_args: ["help_template", "help_ex"]
      }
    }
  }
};

// Recursively render fields and sub-fieldsets, with sub-section labels
function renderSection(
  section: string,
  obj: any,
  values: any,
  errors: any,
  handleChange: any,
  prefix: string[] = []
) {
  // Use prefix for all nested keys, including the first section
  const currentPrefix = [...prefix, section];
  return (
    <div
      key={currentPrefix.join(".")}
      className={`mb-4 pl-4 border-l-4 border-blue-200 ${
      // Add grid if this is the last section at the top level
      prefix.length === 0 && section === Object.keys(languageStructure).filter(k => {
        const v = languageStructure[k as keyof typeof languageStructure];
        return typeof v === "object" && v !== null && !Array.isArray(v) && !("value" in v && "template_args" in v);
      }).slice(-1)[0]
        ? "last:col-span-2"
        : ""
      }`}
    >
      <div className="font-semibold text-blue-800 mb-2">{section}</div>
      <fieldset
      key={currentPrefix.join(".")}
      className={`mb-6 w-full rounded p-4 ${
        // Add grid if this is the last section at the top level
        prefix.length === 0 && section === Object.keys(languageStructure).filter(k => {
          const v = languageStructure[k as keyof typeof languageStructure];
          return typeof v === "object" && v !== null && !Array.isArray(v) && !("value" in v && "template_args" in v);
        }).slice(-1)[0]
        ? "grid grid-cols-1 md:grid-cols-2 gap-4"
        : ""
      }`}
      >
      {Object.entries(obj).map(([key, value]) => {
        const fieldKey = [...currentPrefix, key].join(".");
        if (
        typeof value === "object" &&
        value !== null &&
        !Array.isArray(value) &&
        !("value" in value && "template_args" in value)
        ) {
        // It's a nested section
        return renderSection(key, value, values, errors, handleChange, currentPrefix);
        }
        if (
        typeof value === "object" &&
        value !== null &&
        "value" in value &&
        "template_args" in value
        ) {
        // It's a leaf field with value/template_args
        return (
          <div key={fieldKey} className="mb-2">
          <LanguageFormField
            field={fieldKey}
            value={values[fieldKey]}
            onChange={(val: string, errList: string[]) => handleChange(fieldKey, val, errList)}
            errors={errors[fieldKey] || []}
            templateArgs={value.template_args as string[]}
          />
          </div>
        );
        }
        // Should not happen, but fallback
        return null;
      })}
      </fieldset>
    </div>
  );
}

function getSectionFields(obj: any) {
  // Returns [{section, fields: [{key, value}]}], but error/no_access/lang_code are not sections
  const entries = Object.entries(obj);
  const simpleFields: { key: string; value: any; template_args?: string[] }[] = [];
  const sections: { section: string; fields: { key: string; value: any; template_args?: string[] }[] }[] = [];
  for (const [key, value] of entries) {
    if (key === "lang_code") {
      simpleFields.push({ key, value: value, template_args: [] });
    } else if (
      typeof value === "object" &&
      value !== null &&
      "value" in value &&
      "template_args" in value
    ) {
      // Use full path as key for simple fields too
      simpleFields.push({ key, value: value.value, template_args: Array.isArray(value.template_args) ? value.template_args as string[] : [] });
    } else if (typeof value === "object" && value !== null) {
      sections.push({
        section: key,
        fields: flattenFields(value, [key])
      });
    } else {
      simpleFields.push({ key, value: String(value), template_args: [] });
    }
  }
  return { simpleFields, sections };
}

function flattenFields(obj: any, prefix: string[] = []) {
  let fields: { key: string; value: any; template_args: string[] }[] = [];
  for (const k in obj) {
    const value = obj[k];
    if (
      typeof value === "object" &&
      value !== null &&
      !Array.isArray(value) &&
      !("value" in value && "template_args" in value)
    ) {
      fields = fields.concat(flattenFields(value, [...prefix, k]));
    } else if (
      typeof value === "object" &&
      value !== null &&
      "value" in value &&
      "template_args" in value
    ) {
      // Use full path as key for all fields
      fields.push({ key: [...prefix, k].join("."), value: value.value, template_args: value.template_args });
    }
  }
  return fields;
}

function unflattenFields(fields: { [key: string]: string }) {
  const result: any = {};
  Object.entries(fields).forEach(([flatKey, value]) => {
    const keys = flatKey.split(".");
    let curr = result;
    keys.forEach((k, i) => {
      if (i === keys.length - 1) {
        curr[k] = value;
      } else {
        if (!curr[k]) curr[k] = {};
        curr = curr[k];
      }
    });
  });
  return result;
}

function downloadJsonFile(obj: any, langCode: string) {
  const dataStr = JSON.stringify(obj, null, 2);
  const blob = new Blob([dataStr], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${langCode || "language"}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

const LanguageForm = () => {
  const { simpleFields, sections } = getSectionFields(languageStructure);
  const flatFields = [
    ...simpleFields,
    ...sections.flatMap(s => s.fields)
  ];
  const [values, setValues] = useState<{ [key: string]: string }>(
    Object.fromEntries(flatFields.map((f) => [f.key, f.value]))
  );
  const [errors, setErrors] = useState<{ [key: string]: string[] }>({});
  const [submitMessage, setSubmitMessage] = useState<string | null>(null);

  const handleChange = (key: string, value: string, errorList: string[]) => {
    setValues((prev) => ({ ...prev, [key]: value }));
    setErrors((prev) => ({ ...prev, [key]: errorList }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setSubmitMessage(null);
    const hasError = Object.values(errors).some((errs) => errs && errs.length > 0);
    if (hasError) {
      setSubmitMessage("Please fix all errors before submitting.");
      return;
    }
    const emptyFields = flatFields.filter(f => !values[f.key]);
    if (emptyFields.length > 0) {
      setSubmitMessage("Please fill all fields.");
      return;
    }
    const result = unflattenFields(values);
    setSubmitMessage("Downloading will start soon...");
    const langCode = values["lang_code"] || "language";
    downloadJsonFile(result, langCode);
  };

  return (
    <form onSubmit={handleSubmit} className="w-full mx-auto p-4">
      <h2 className="text-xl font-bold mb-4 text-blue-950">Language Creator</h2>
      {/* Render simple fields (not in sections) */}
      <div className="mb-6">
        {simpleFields.map(({ key, template_args }) => (
          <div key={key} className="flex-1">
            <LanguageFormField
              field={key}
              value={values[key]}
              onChange={(val, errList) => handleChange(key, val, errList)}
              errors={errors[key] || []}
              templateArgs={template_args}
            />
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {/* Render sections and sub-fieldsets recursively with sub-section labels */}
      {sections.map(({ section }) =>
        renderSection(
          section,
          languageStructure[section as keyof typeof languageStructure],
          values,
          errors,
          handleChange
        )
      )}
      </div>
      <button
        type="submit"
        className="mt-4 px-6 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
      >
        Save Language
      </button>
      {submitMessage && (
        <div className={`mt-4 text-center text-base ${submitMessage.startsWith("Please") ? "text-red-600" : "text-green-700"}`}>
          {submitMessage}
        </div>
      )}
    </form>
  );
};

export default LanguageForm;