(function () {
  "use strict";

  const PER_PAGE = 24;
  let allItems = [];
  let filtered = [];
  let currentPage = 1;
  let viewMode = localStorage.getItem("viewMode") || "grid";
  let sortField = "title";
  let sortAsc = true;
  let activeFilters = {};

  const I18N = window.CATALOGUE_I18N || {
    decade: "Decade", language: "Language", item_type: "Type",
    place: "Place", publisher: "Publisher", author: "Author", series: "Series"
  };

  // Checkbox filter facets (small cardinality)
  const CHECKBOX_FACETS = [
    { key: "decade", label: I18N.decade, field: "decade" },
    { key: "languages", label: I18N.language, field: "languages", isArray: true },
    { key: "item_types", label: I18N.item_type, field: "item_types", isArray: true },
  ];

  // Searchable dropdown facets (large cardinality)
  const DROPDOWN_FACETS = [
    { key: "place", label: I18N.place, field: "place" },
    { key: "publishers", label: I18N.publisher, field: "publishers", isArray: true },
    { key: "authors", label: I18N.author, field: "authors", isArray: true },
    { key: "series", label: I18N.series, field: "series", isArray: true },
  ];

  // --- Init ---
  document.addEventListener("DOMContentLoaded", init);

  function init() {
    // Detect JSON URL from the current page URL
    var path = window.location.pathname;
    // The catalogue page is at /zapata-library/es/catalogue/ or /zapata-library/en/catalogue/
    var jsonUrl = path.replace(/\/$/, "") + "/index.json";

    fetch(jsonUrl)
      .then(function (r) { return r.json(); })
      .then(function (data) {
        allItems = data;
        filtered = allItems.slice();
        document.getElementById("loading").style.display = "none";
        buildFilters();
        applySort();
        render();
        bindEvents();
        restoreViewMode();
      })
      .catch(function (err) {
        document.getElementById("loading").textContent = "Error loading catalogue data.";
        console.error(err);
      });
  }

  // --- Filter building ---
  function buildFilters() {
    var container = document.getElementById("filter-groups");
    container.innerHTML = "";

    CHECKBOX_FACETS.forEach(function (facet) {
      var values = collectValues(facet.field, facet.isArray);
      if (values.length === 0) return;
      // Sort decades descending, others by count
      if (facet.key === "decade") {
        values.sort(function (a, b) { return b.value.localeCompare(a.value); });
      }
      container.appendChild(buildCheckboxGroup(facet, values));
    });

    DROPDOWN_FACETS.forEach(function (facet) {
      var values = collectValues(facet.field, facet.isArray);
      if (values.length === 0) return;
      container.appendChild(buildDropdownGroup(facet, values));
    });
  }

  function collectValues(field, isArray) {
    var counts = {};
    allItems.forEach(function (item) {
      var val = item[field];
      if (isArray && Array.isArray(val)) {
        val.forEach(function (v) {
          if (v) counts[v] = (counts[v] || 0) + 1;
        });
      } else if (val) {
        counts[val] = (counts[val] || 0) + 1;
      }
    });
    return Object.keys(counts)
      .map(function (k) { return { value: k, count: counts[k] }; })
      .sort(function (a, b) { return b.count - a.count; });
  }

  function buildCheckboxGroup(facet, values) {
    var group = document.createElement("div");
    group.className = "filter-group";
    var bodyId = "fg-" + facet.key;
    group.innerHTML =
      '<div class="filter-group-title" data-toggle="' + facet.key + '"' +
      ' role="button" tabindex="0" aria-expanded="true" aria-controls="' + bodyId + '">' +
      facet.label + ' <span class="caret" aria-hidden="true">&#9662;</span></div>';
    var list = document.createElement("div");
    list.className = "filter-group-body";
    list.id = bodyId;
    values.forEach(function (v) {
      var label = document.createElement("label");
      label.className = "filter-checkbox";
      label.innerHTML =
        '<input type="checkbox" data-facet="' + facet.key + '" value="' +
        escapeAttr(v.value) + '"> ' +
        escapeHtml(v.value) + ' <span class="filter-count">(' + v.count + ")</span>";
      list.appendChild(label);
    });
    group.appendChild(list);
    return group;
  }

  function buildDropdownGroup(facet, values) {
    var group = document.createElement("div");
    group.className = "filter-group";
    var bodyId = "fg-" + facet.key;
    group.innerHTML =
      '<div class="filter-group-title" data-toggle="' + facet.key + '"' +
      ' role="button" tabindex="0" aria-expanded="true" aria-controls="' + bodyId + '">' +
      facet.label + ' <span class="caret" aria-hidden="true">&#9662;</span></div>';
    var body = document.createElement("div");
    body.className = "filter-group-body";
    body.id = "fg-" + facet.key;

    var input = document.createElement("input");
    input.type = "text";
    input.className = "filter-dropdown-search";
    input.placeholder = "Search...";
    input.setAttribute("data-facet-search", facet.key);
    body.appendChild(input);

    var list = document.createElement("div");
    list.className = "filter-dropdown-list";
    list.setAttribute("data-facet-list", facet.key);
    values.slice(0, 50).forEach(function (v) {
      var btn = document.createElement("button");
      btn.className = "filter-dropdown-item";
      btn.setAttribute("data-facet", facet.key);
      btn.setAttribute("data-value", v.value);
      btn.innerHTML = escapeHtml(v.value) + ' <span class="filter-count">(' + v.count + ")</span>";
      list.appendChild(btn);
    });
    // Store all values for search
    list.setAttribute("data-all-values", JSON.stringify(values));
    body.appendChild(list);
    group.appendChild(body);
    return group;
  }

  // --- Events ---
  function bindEvents() {
    // Text search
    document.getElementById("search-input").addEventListener("input", debounce(function () {
      currentPage = 1;
      applyFilters();
    }, 200));

    // Checkbox filters
    document.getElementById("filter-groups").addEventListener("change", function (e) {
      if (e.target.type === "checkbox") {
        currentPage = 1;
        syncCheckboxFilters();
        applyFilters();
      }
    });

    // Dropdown item clicks
    document.getElementById("filter-groups").addEventListener("click", function (e) {
      var item = e.target.closest(".filter-dropdown-item");
      if (item) {
        var facet = item.getAttribute("data-facet");
        var value = item.getAttribute("data-value");
        if (!activeFilters[facet]) activeFilters[facet] = [];
        if (activeFilters[facet].indexOf(value) === -1) {
          activeFilters[facet].push(value);
        }
        currentPage = 1;
        applyFilters();
      }
    });

    // Dropdown search inputs
    document.getElementById("filter-groups").addEventListener("input", function (e) {
      if (e.target.hasAttribute("data-facet-search")) {
        var facetKey = e.target.getAttribute("data-facet-search");
        var query = e.target.value.toLowerCase();
        var listEl = document.querySelector('[data-facet-list="' + facetKey + '"]');
        var allValues = JSON.parse(listEl.getAttribute("data-all-values"));
        var matches = allValues.filter(function (v) {
          return v.value.toLowerCase().indexOf(query) !== -1;
        }).slice(0, 50);
        listEl.innerHTML = "";
        matches.forEach(function (v) {
          var btn = document.createElement("button");
          btn.className = "filter-dropdown-item";
          btn.setAttribute("data-facet", facetKey);
          btn.setAttribute("data-value", v.value);
          btn.innerHTML = escapeHtml(v.value) + ' <span class="filter-count">(' + v.count + ")</span>";
          listEl.appendChild(btn);
        });
      }
    });

    // Filter group toggle (collapse/expand) — mouse and keyboard
    function toggleFilterGroup(title) {
      var group = title.parentElement;
      var collapsed = group.classList.toggle("collapsed");
      title.setAttribute("aria-expanded", collapsed ? "false" : "true");
    }
    document.getElementById("filter-groups").addEventListener("click", function (e) {
      var title = e.target.closest(".filter-group-title");
      if (title) toggleFilterGroup(title);
    });
    document.getElementById("filter-groups").addEventListener("keydown", function (e) {
      if (e.key === "Enter" || e.key === " ") {
        var title = e.target.closest(".filter-group-title");
        if (title) { e.preventDefault(); toggleFilterGroup(title); }
      }
    });

    // Active filter chip removal
    document.getElementById("active-filters").addEventListener("click", function (e) {
      var chip = e.target.closest(".filter-chip");
      if (chip) {
        var facet = chip.getAttribute("data-facet");
        var value = chip.getAttribute("data-value");
        removeFilter(facet, value);
        currentPage = 1;
        applyFilters();
      }
    });

    // Clear all
    document.getElementById("clear-all").addEventListener("click", function () {
      activeFilters = {};
      document.getElementById("search-input").value = "";
      document.querySelectorAll('#filter-groups input[type="checkbox"]').forEach(function (cb) {
        cb.checked = false;
      });
      currentPage = 1;
      applyFilters();
    });

    // View toggle
    document.getElementById("view-grid").addEventListener("click", function () { setViewMode("grid"); });
    document.getElementById("view-table").addEventListener("click", function () { setViewMode("table"); });

    // Mobile filter toggle
    document.getElementById("filter-toggle-btn").addEventListener("click", function () {
      var open = document.getElementById("filters").classList.toggle("open");
      this.setAttribute("aria-expanded", open ? "true" : "false");
    });

    // Mobile filter close
    document.getElementById("filter-close-btn").addEventListener("click", function () {
      document.getElementById("filters").classList.remove("open");
      document.getElementById("filter-toggle-btn").setAttribute("aria-expanded", "false");
    });

    // Table header sort
    document.getElementById("results").addEventListener("click", function (e) {
      var th = e.target.closest("[data-sort]");
      if (th) {
        var field = th.getAttribute("data-sort");
        if (sortField === field) {
          sortAsc = !sortAsc;
        } else {
          sortField = field;
          sortAsc = true;
        }
        applySort();
        render();
      }
    });
  }

  // --- Filtering ---
  function syncCheckboxFilters() {
    // Rebuild activeFilters for checkbox facets from DOM
    CHECKBOX_FACETS.forEach(function (facet) {
      var checked = [];
      document.querySelectorAll('input[data-facet="' + facet.key + '"]:checked').forEach(function (cb) {
        checked.push(cb.value);
      });
      if (checked.length > 0) {
        activeFilters[facet.key] = checked;
      } else {
        delete activeFilters[facet.key];
      }
    });
  }

  function removeFilter(facet, value) {
    if (!activeFilters[facet]) return;
    activeFilters[facet] = activeFilters[facet].filter(function (v) { return v !== value; });
    if (activeFilters[facet].length === 0) delete activeFilters[facet];
    // Uncheck checkbox if applicable
    var cb = document.querySelector('input[data-facet="' + facet + '"][value="' + CSS.escape(value) + '"]');
    if (cb) cb.checked = false;
  }

  function applyFilters() {
    var query = document.getElementById("search-input").value.toLowerCase().trim();

    filtered = allItems.filter(function (item) {
      // Text search
      if (query) {
        var haystack = (item.title + " " + (item.authors || []).join(" ") + " " + (item.subjects || []).join(" ")).toLowerCase();
        if (haystack.indexOf(query) === -1) return false;
      }

      // Facet filters (AND across facets, OR within a facet)
      for (var facet in activeFilters) {
        var values = activeFilters[facet];
        if (!values || values.length === 0) continue;
        var itemVal = item[facet];
        var match = false;
        if (Array.isArray(itemVal)) {
          match = values.some(function (v) { return itemVal.indexOf(v) !== -1; });
        } else {
          match = values.indexOf(itemVal) !== -1;
        }
        if (!match) return false;
      }
      return true;
    });

    applySort();
    renderActiveChips();
    render();
  }

  // --- Sorting ---
  function applySort() {
    filtered.sort(function (a, b) {
      var va = a[sortField] || "";
      var vb = b[sortField] || "";
      if (Array.isArray(va)) va = va[0] || "";
      if (Array.isArray(vb)) vb = vb[0] || "";
      if (typeof va === "number" && typeof vb === "number") {
        return sortAsc ? va - vb : vb - va;
      }
      va = String(va).toLowerCase();
      vb = String(vb).toLowerCase();
      if (va < vb) return sortAsc ? -1 : 1;
      if (va > vb) return sortAsc ? 1 : -1;
      return 0;
    });
  }

  // --- Rendering ---
  function render() {
    var totalPages = Math.ceil(filtered.length / PER_PAGE) || 1;
    if (currentPage > totalPages) currentPage = totalPages;
    var start = (currentPage - 1) * PER_PAGE;
    var pageItems = filtered.slice(start, start + PER_PAGE);

    var resultsEl = document.getElementById("results");
    var countEl = document.getElementById("results-count");
    countEl.textContent = filtered.length + " / " + allItems.length;

    if (filtered.length === 0) {
      resultsEl.innerHTML = '<div class="no-results">No matches found</div>';
      document.getElementById("pagination").innerHTML = "";
      return;
    }

    if (viewMode === "table") {
      resultsEl.innerHTML = renderTable(pageItems);
    } else {
      resultsEl.innerHTML = renderGrid(pageItems);
    }

    renderPagination(totalPages);
  }

  function renderGrid(items) {
    return '<div class="book-grid">' +
      items.map(function (item) {
        return '<article class="book-card"><a href="' + escapeAttr(item.url) + '">' +
          '<div class="book-cover"><img src="' + escapeAttr(item.cover) + '" alt="' + escapeAttr(item.title) + '" loading="lazy" onerror="this.style.display=\'none\'"></div>' +
          '<div class="book-info">' +
          '<h3 class="book-title">' + escapeHtml(item.title) + '</h3>' +
          (item.authors && item.authors.length ? '<p class="book-author">' + escapeHtml(item.authors.join(", ")) + '</p>' : '') +
          (item.year ? '<span class="book-year">' + item.year + '</span>' : '') +
          '</div></a></article>';
      }).join("") +
      '</div>';
  }

  function renderTable(items) {
    var arrow = function (field) {
      if (sortField !== field) return "";
      return sortAsc ? " &#9650;" : " &#9660;";
    };
    var ariaSort = function (field) {
      if (sortField !== field) return ' aria-sort="none"';
      return sortAsc ? ' aria-sort="ascending"' : ' aria-sort="descending"';
    };
    return '<div class="table-wrapper"><table class="catalogue-table">' +
      '<thead><tr>' +
      '<th data-sort="title"' + ariaSort("title") + '>Title' + arrow("title") + '</th>' +
      '<th data-sort="authors"' + ariaSort("authors") + '>Author' + arrow("authors") + '</th>' +
      '<th data-sort="year"' + ariaSort("year") + '>Year' + arrow("year") + '</th>' +
      '<th data-sort="publishers" class="hide-mobile"' + ariaSort("publishers") + '>Publisher' + arrow("publishers") + '</th>' +
      '<th data-sort="place" class="hide-mobile"' + ariaSort("place") + '>Place' + arrow("place") + '</th>' +
      '<th class="hide-tablet">Language</th>' +
      '<th class="hide-tablet">Pages</th>' +
      '<th class="hide-tablet">Type</th>' +
      '</tr></thead><tbody>' +
      items.map(function (item) {
        return '<tr onclick="window.location=\'' + escapeAttr(item.url) + '\'">' +
          '<td><a href="' + escapeAttr(item.url) + '">' + escapeHtml(item.title) + '</a></td>' +
          '<td>' + escapeHtml((item.authors || []).join("; ")) + '</td>' +
          '<td>' + (item.year || "") + '</td>' +
          '<td class="hide-mobile">' + escapeHtml((item.publishers || []).join("; ")) + '</td>' +
          '<td class="hide-mobile">' + escapeHtml(item.place || "") + '</td>' +
          '<td class="hide-tablet">' + escapeHtml((item.languages || []).join(", ")) + '</td>' +
          '<td class="hide-tablet">' + (item.pages || "") + '</td>' +
          '<td class="hide-tablet">' + escapeHtml((item.item_types || []).join(", ")) + '</td>' +
          '</tr>';
      }).join("") +
      '</tbody></table></div>';
  }

  function renderPagination(totalPages) {
    var pag = document.getElementById("pagination");
    if (totalPages <= 1) { pag.innerHTML = ""; return; }

    var html = "";
    if (currentPage > 1) {
      html += '<button data-page="' + (currentPage - 1) + '" aria-label="Previous page">&laquo;</button>';
    }

    var start = Math.max(1, currentPage - 3);
    var end = Math.min(totalPages, currentPage + 3);
    for (var i = start; i <= end; i++) {
      var isCurrent = i === currentPage;
      html += '<button data-page="' + i + '"' +
        (isCurrent ? ' class="active" aria-current="page"' : '') +
        ' aria-label="Page ' + i + '">' + i + '</button>';
    }

    if (currentPage < totalPages) {
      html += '<button data-page="' + (currentPage + 1) + '" aria-label="Next page">&raquo;</button>';
    }

    pag.innerHTML = html;
    pag.onclick = function (e) {
      var btn = e.target.closest("[data-page]");
      if (btn) {
        currentPage = parseInt(btn.getAttribute("data-page"));
        render();
        window.scrollTo({ top: 0, behavior: "smooth" });
      }
    };
  }

  function renderActiveChips() {
    var container = document.getElementById("active-filters");
    var html = "";
    for (var facet in activeFilters) {
      activeFilters[facet].forEach(function (value) {
        html += '<button class="filter-chip" data-facet="' + escapeAttr(facet) + '" data-value="' + escapeAttr(value) + '">' +
          escapeHtml(value) + ' <span aria-hidden="true">&times;</span><span class="sr-only"> — remove filter</span></button>';
      });
    }
    container.innerHTML = html;
  }

  // --- View mode ---
  function setViewMode(mode) {
    viewMode = mode;
    localStorage.setItem("viewMode", mode);
    document.getElementById("view-grid").classList.toggle("active", mode === "grid");
    document.getElementById("view-grid").setAttribute("aria-pressed", mode === "grid" ? "true" : "false");
    document.getElementById("view-table").classList.toggle("active", mode === "table");
    document.getElementById("view-table").setAttribute("aria-pressed", mode === "table" ? "true" : "false");
    render();
  }

  function restoreViewMode() {
    document.getElementById("view-grid").classList.toggle("active", viewMode === "grid");
    document.getElementById("view-grid").setAttribute("aria-pressed", viewMode === "grid" ? "true" : "false");
    document.getElementById("view-table").classList.toggle("active", viewMode === "table");
    document.getElementById("view-table").setAttribute("aria-pressed", viewMode === "table" ? "true" : "false");
  }

  // --- Utilities ---
  function escapeHtml(s) {
    if (!s) return "";
    var div = document.createElement("div");
    div.appendChild(document.createTextNode(s));
    return div.innerHTML;
  }

  function escapeAttr(s) {
    if (!s) return "";
    return s.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/'/g, "&#39;").replace(/</g, "&lt;");
  }

  function debounce(fn, delay) {
    var timer;
    return function () {
      clearTimeout(timer);
      timer = setTimeout(fn, delay);
    };
  }
})();
