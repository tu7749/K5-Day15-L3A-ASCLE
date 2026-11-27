const DESTINATIONS = {
  ha_giang: {name:"Hà Giang", area:"Miền núi phía Bắc", highlight:"Mã Pí Lèng · Sông Nho Quế", asset:"ha-giang.webp", alt:"Sông Nho Quế quanh co giữa núi đá Hà Giang", center:[22.82,104.98]},
  da_nang: {name:"Đà Nẵng", area:"Duyên hải miền Trung", highlight:"Bán đảo Sơn Trà · Biển Mỹ Khê", asset:"da-nang.webp", alt:"Đường bờ biển Mỹ Khê và thành phố Đà Nẵng nhìn từ trên cao", center:[16.05,108.20]},
};
const COSTS = {ticket:"Vé tham quan", transport:"Di chuyển", food:"Ăn uống", lodging:"Lưu trú"};
const formatter = new Intl.NumberFormat("vi-VN");
const money = value => formatter.format(value) + " ₫";
const esc = value => String(value ?? "").replace(/[&<>"']/g, character => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"})[character]);
const source = (value, label="Nguồn") => {
  try {
    const url = new URL(value);
    if (!["http:", "https:"].includes(url.protocol)) return "";
    return '<a class="vd-source" target="_blank" rel="noopener noreferrer" href="' + esc(url.href) + '">' + esc(label) + '</a>';
  } catch { return ""; }
};
const amountSpan = amount => '<strong>' + money(amount) + '</strong>';
const range = rate => rate.low === rate.high ? money(rate.high) : money(rate.low) + " – " + money(rate.high);

function weatherText(weather) {
  if (weather.source === "forecast") {
    const metrics = [];
    if (weather.temperature_min != null && weather.temperature_max != null) metrics.push(weather.temperature_min + "–" + weather.temperature_max + " °C");
    if (weather.rain_probability != null) metrics.push("Mưa " + weather.rain_probability + "%");
    if (weather.rain_mm != null) metrics.push(weather.rain_mm + " mm");
    if (weather.weather_code != null) {
      const code = weather.weather_code;
      const label = code >= 95 ? "Dông" : code >= 51 && code <= 86 ? "Có mưa hoặc giáng thủy" : code === 0 ? "Trời quang" : "Có mây hoặc sương";
      metrics.push(label);
    }
    return "Dự báo" + (metrics.length ? " · " + metrics.join(" · ") : "");
  }
  if (weather.source === "history") {
    return "Tần suất mưa lịch sử · " + formatter.format(Math.round(100 * weather.wet_days / weather.total_days)) +
      "% (" + weather.wet_days + "/" + weather.total_days + " ngày có ít nhất 1 mm, " +
      weather.reference_start + "–" + weather.reference_end + ")";
  }
  return "Chưa có dữ liệu thời tiết";
}

function renderBudget(plan) {
  const status = {
    within: "Trong ngân sách theo các mức giá và khoản dự trù ở trên.",
    partial: "Chưa thể kết luận trong ngân sách vì còn khoản chưa tính.",
    over: "Các khoản đã tính và dự trù vượt ngân sách.",
  }[plan.budget_status];
  const items = Object.entries(plan.costs).map(([key, bucket]) => '<li><b>' + COSTS[key] + '</b> · ' +
    (bucket.entries.length ? money(bucket.amount) : bucket.missing.length ? "Chưa có giá" : "Không phát sinh theo lịch") +
    (bucket.allowance ? " · Dự trù " + money(bucket.allowance) : "") +
    (bucket.entries.length ? '<ul>' + bucket.entries.map(row => '<li>' + esc(row.name) + ' · ' + money(row.amount) + ' ' + source(row.source) + '</li>').join("") + '</ul>' : "") +
    (bucket.missing.length ? '<div>' + (bucket.allowance ? 'Đã dự trù: ' : 'Chưa tính: ') + esc(bucket.missing.join("; ")) + '</div>' : "") +
    '</li>').join("");
  return '<div class="vd-budget"><div><span>Tổng đã tính</span>' + amountSpan(plan.total_known) +
    '</div><div><span>Ngân sách nhóm</span>' + amountSpan(plan.budget) +
    '</div><div><span>' + (plan.budget_status === "partial" ? "Còn lại tạm tính" : "Còn lại") + '</span>' +
    amountSpan(plan.remaining) + '</div></div><p class="vd-status ' + esc(plan.budget_status) + '">' + esc(status) +
    (plan.total_reserved ? " Tổng dự trù: " + money(plan.total_reserved) + "." : "") +
    '</p><details class="vd-costs"><summary>Các khoản chi và khoản còn thiếu</summary><ul>' + items + '</ul></details>';
}

function renderDay(day) {
  const stops = day.items.map((item, index) => '<li><span class="vd-order">' + (index + 1) +
    '</span><div><h3>' + esc(item.name) + '</h3><p>' +
    (item.arrival ? "Đến " + esc(item.arrival) : "Chưa xác định giờ đến") +
    ' · ' + item.duration + ' phút' + (item.duration_estimate ? " (ước tính)" : "") +
    (item.indoor ? ' · Trong nhà' : '') + '</p><p>' +
    (item.included ? "Vé đã gồm trong khu" : item.fee == null ? "Chưa có giá vé" : "Vé nhóm " + money(item.fee)) +
    ' ' + source(item.fee_source || item.source) + '</p>' +
    (!item.has_hours ? '<p class="vd-missing">Chưa có giờ mở cửa, cần kiểm tra trước khi đi.</p>' : "") +
    (!item.leg ? '<p class="vd-missing">Thiếu tuyến từ ' + esc(item.from_name) + ' theo phương tiện đã chọn.</p>' :
      item.leg.minutes ? '<p>' + item.leg.minutes + ' phút di chuyển' + (item.leg.source && !source(item.leg.source) ? ' · ' + esc(item.leg.source) : ' ' + source(item.leg.source, "Nguồn tuyến")) + '</p>' : "") +
    '</div></li>').join("");
  const hotels = day.lodgings?.map(place => '<article class="vd-hotel"><h3>' + esc(place.name) + '</h3><p>' + esc(place.area) +
      (place.distance != null ? ' · ' + formatter.format(place.distance) + ' km đường chim bay' : '') + '</p><p class="' +
      (place.computed ? '' : 'vd-missing') + '">' +
      (place.computed ? range(place.computed) + ' cho ' + place.computed.rooms + ' ' + esc(place.computed.unit) +
        '/đêm' + (place.selected ? ' · Đã tính vào dự toán' : '') : 'Tham khảo từ ' + money(place.reference_from) + '/đêm') +
      '</p>' + source(place.source, "Nguồn giá") + '</article>').join("");
  const hotelGroup = day.lodgings ? '<section class="vd-hotel-list"><h3>Chỗ nghỉ cuối ngày</h3>' +
    (hotels || '<p>Chưa có chỗ nghỉ phù hợp theo dữ liệu hiện có.</p>') +
    (day.lodging_reference ? '<p>Giá niêm yết tham khảo theo vùng: từ ' +
      money(day.lodging_reference.median) + '/đêm (trung vị; chưa quy đổi đơn vị).</p>' : '') + '</section>' : '';
  return '<time datetime="' + esc(day.date) + '">' + esc(day.date.split("-").reverse().join("/")) + '</time>' +
    '<p class="vd-weather">' + esc(weatherText(day.weather)) + ' ' + source(day.weather.source_url, "Open-Meteo") +
    (day.reason ? '<br>' + esc(day.reason) : '') + '</p>' +
    (day.ai_selection ? '<p class="vd-ai">AI chọn từ ' + esc(day.ai_selection.candidate_count) +
      ' điểm trong nhà đã kiểm tra · ' + esc(day.ai_selection.model) + ' · ' + esc(day.ai_selection.tokens_in) +
      ' token vào / ' + esc(day.ai_selection.tokens_out) + ' token ra</p>' : '') +
    (stops ? '<ol class="vd-events">' + stops + '</ol>' : '<p>Chưa tìm được điểm phù hợp cho ngày này.</p>') +
    (day.return_missing ? '<p class="vd-weather">Thiếu tuyến về ' + esc(day.origin) + ' theo phương tiện đã chọn.</p>' : '') +
    hotelGroup;
}

function loadMap(day, plan, mapElement, noteElement) {
  const L = window.L;
  if (!L) { noteElement.textContent = "Chưa tải được bản đồ. Lịch trình vẫn hiển thị."; return; }
  const map = L.map(mapElement, {scrollWheelZoom:false, zoomAnimation:false, fadeAnimation:false,
    markerZoomAnimation:false}).setView(DESTINATIONS[plan.region].center, 11, {animate:false});
  let tilesFailed = false;
  const tiles = L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 19, attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
  }).addTo(map);
  tiles.on("tileerror", () => {
    if (!tilesFailed) noteElement.textContent = "Chưa tải được nền OpenStreetMap. Các ghim vẫn hiển thị.";
    tilesFailed = true;
  });
  const points = [];
  const center = day.origin_point && [day.origin_point.lat, day.origin_point.lon];
  if (center) {
    const tooltip = document.createElement("span");
    tooltip.textContent = day.origin || "Điểm xuất phát";
    L.marker(center, {alt:"Điểm xuất phát", icon:L.divIcon({className:"", html:'<span class="vd-pin vd-start-pin">●</span>', iconSize:[24,24]})})
      .bindTooltip(tooltip).addTo(map);
    points.push(center);
  }
  let last = center;
  day.items.forEach((item, index) => {
    const point = [item.lat, item.lon];
    const title = (index + 1) + ". " + item.name;
    const tooltip = document.createElement("span");
    tooltip.textContent = title;
    L.marker(point, {alt:title, title, icon:L.divIcon({className:"", html:'<span class="vd-pin">' + (index + 1) + '</span>', iconSize:[24,24]})})
      .bindTooltip(tooltip).addTo(map);
    if (last && item.leg?.minutes) L.polyline([last, point], {color:"#275b57", dashArray:"5 7", weight:3}).addTo(map);
    last = point;
    points.push(point);
  });
  if (last && center && day.return_leg?.minutes) L.polyline([last, center], {color:"#856938", dashArray:"5 7", weight:2}).addTo(map);
  if (points.length > 1) map.fitBounds(points, {padding:[24,24], maxZoom:14, animate:false});
  else if (points.length) map.setView(points[0], 13, {animate:false});
  return map;
}

function clearMap(result) {
  if (!result.vdMap) return;
  result.vdMap.stop().remove();
  result.vdMap = null;
}

function renderPlan(result, plan) {
  if (result.vdResize) result.vdResize.disconnect();
  clearMap(result);
  result.hidden = false;
  result.innerHTML = '<h2 id="vd-results-title" tabindex="-1">Lịch trình ' + esc(plan.name) + '</h2>' +
    renderBudget(plan) + '<div class="vd-tabs" role="tablist" aria-label="Ngày trong chuyến đi">' +
    plan.days.map((_, i) => '<button type="button" id="vd-tab-' + i + '" role="tab" aria-controls="vd-day" aria-selected="false" tabindex="-1">Ngày ' + (i + 1) + '</button>').join("") +
    '</div><div class="vd-view" aria-label="Chế độ xem"><button type="button" aria-pressed="true">Lịch trình</button><button type="button" aria-pressed="false">Bản đồ</button></div>' +
    '<div class="vd-trip-grid"><div class="vd-day-panel"><div class="vd-day" id="vd-day" role="tabpanel"></div></div>' +
    '<aside class="vd-map-box"><h3>Bản đồ tuyến tham quan</h3><div class="vd-map" aria-label="Bản đồ địa điểm"></div><p class="vd-map-note">Các ghim và đường nối thể hiện thứ tự tham quan.</p></aside></div>' +
    (plan.summary ? '<details class="vd-summary"><summary>Tóm tắt lịch trình</summary><p style="white-space:pre-line">' + esc(plan.summary) + '</p></details>' : '');
  const dayPanel = result.querySelector("#vd-day");
  const mapElement = result.querySelector(".vd-map");
  const note = result.querySelector(".vd-map-note");
  const tabs = Array.from(result.querySelectorAll('[role="tab"]'));
  const grid = result.querySelector(".vd-trip-grid");
  const viewButtons = result.querySelectorAll(".vd-view button");
  let selectedIndex = 0;
  let mapFitted = false;
  const openMap = () => {
    if (!mapElement.offsetWidth || mapFitted) return;
    note.textContent = "Các ghim và đường nối thể hiện thứ tự tham quan.";
    result.vdMap = loadMap(plan.days[selectedIndex], plan, mapElement, note);
    mapFitted = !!result.vdMap;
  };
  const select = (index, focus) => {
    selectedIndex = index;
    tabs.forEach((tab, i) => {
      tab.setAttribute("aria-selected", String(i === index));
      tab.tabIndex = i === index ? 0 : -1;
    });
    dayPanel.setAttribute("aria-labelledby", tabs[index].id);
    dayPanel.innerHTML = renderDay(plan.days[index]);
    clearMap(result);
    mapFitted = false;
    openMap();
    if (focus) tabs[index].focus();
  };
  tabs.forEach((tab, index) => {
    tab.onclick = () => select(index, false);
    tab.onkeydown = event => {
      const next = {"ArrowLeft":(index+tabs.length-1)%tabs.length, "ArrowRight":(index+1)%tabs.length, Home:0, End:tabs.length-1}[event.key];
      if (next != null) { event.preventDefault(); select(next, true); }
    };
  });
  viewButtons.forEach((button, index) => {
    button.onclick = () => {
      grid.classList.toggle("is-map", index === 1);
      viewButtons.forEach((item, i) => item.setAttribute("aria-pressed", String(index === i)));
      if (index === 1) requestAnimationFrame(() => { openMap(); result.vdMap?.invalidateSize({pan:false}); });
    };
  });
  result.vdResize = new ResizeObserver(() => { openMap(); if (mapElement.offsetWidth) result.vdMap?.invalidateSize({pan:false}); });
  result.vdResize.observe(mapElement);
  select(0, false);
}

export default function ({data, parentElement, setTriggerValue}) {
  const view = parentElement.querySelector(".vietdu");
  if (!view) return;
  const asset = name => data.asset_base + name;
  const form = view.querySelector("#vd-form");
  const field = name => form.elements.namedItem(name);
  const error = view.querySelector("#vd-form-error");
  const primary = form.querySelector(".vd-primary");
  const cover = view.querySelector("#vd-cover");
  const results = view.querySelector("#vd-results");
  const displayError = message => { error.textContent = message; error.hidden = !message; };
  const switchRegion = (region, origin=null) => {
    const place = DESTINATIONS[region];
    if (!place) return;
    field("region").value = region;
    if (cover.getAttribute("src") !== asset(place.asset)) cover.src = asset(place.asset);
    cover.alt = place.alt;
    view.querySelector("#vd-cover-title").textContent = place.name;
    view.querySelector("#vd-province").textContent = place.area;
    view.querySelector("#vd-cover-place").textContent = place.highlight;
    const options = data.origins[region].map(option => new Option(option.name, option.id));
    field("origin").replaceChildren(new Option("Trung tâm điểm đến", ""), ...options);
    if (origin !== null && options.some(option => option.value === origin)) field("origin").value = origin;
  };
  if (!form.dataset.ready) {
    form.dataset.ready = "1";
    form.querySelector("#vd-interests").replaceChildren(...Object.entries(data.interests).map(([value, label]) => {
      const node = document.createElement("label");
      const box = Object.assign(document.createElement("input"), {type:"checkbox", name:"interests", value});
      node.append(box, document.createTextNode(label));
      return node;
    }));
    for (const thumbnail of view.querySelectorAll("img[data-asset]")) thumbnail.src = asset(thumbnail.dataset.asset);
    const values = data.values;
    for (const name of ["departure", "days", "people", "budget", "mode", "lodging_type"]) {
      if (values[name] != null) field(name).value = name === "budget" ? formatter.format(values[name]) : values[name];
    }
    for (const box of form.querySelectorAll('[name="interests"]')) box.checked = (values.interests || []).includes(box.value);
    for (const key of Object.keys(COSTS)) if (values.allowances?.[key] != null) field("allow_" + key).value = values.allowances[key];
    field("departure").min = data.today;
    if (!field("departure").value) field("departure").value = data.tomorrow;
    switchRegion(values.region || "ha_giang", values.origin || "");
  }
  field("region").onchange = () => { switchRegion(field("region").value); };
  field("budget").onblur = () => {
    const value = field("budget").value.trim();
    if (/^(?:\d+|\d{1,3}(?:[., ]\d{3})+)$/.test(value)) field("budget").value = formatter.format(Number(value.replace(/[., ]/g, "")));
  };
  for (const button of view.querySelectorAll(".vd-destination")) {
    button.onclick = () => { switchRegion(button.dataset.region); view.querySelector("#lap-lich").scrollIntoView({block:"start"}); field("region").focus({preventScroll:true}); };
  }
  form.onsubmit = event => {
    event.preventDefault();
    const budgetValue = field("budget").value.trim();
    if (!/^(?:\d+|\d{1,3}(?:[., ]\d{3})+)$/.test(budgetValue) || Number(budgetValue.replace(/[., ]/g, "")) <= 0) {
      displayError("Nhập tổng ngân sách bằng VNĐ, lớn hơn 0."); field("budget").focus(); return;
    }
    if (!field("departure").value || field("departure").value < data.today) {
      displayError("Chọn ngày đi từ hôm nay trở đi."); field("departure").focus(); return;
    }
    for (const [name, label, max] of [["days", "Số ngày", 5], ["people", "Số khách", 99]]) {
      const value = Number(field(name).value);
      if (!Number.isInteger(value) || value < 1 || value > max) {
        displayError(label + " phải là số nguyên từ 1 đến " + max + "."); field(name).focus(); return;
      }
    }
    const fields = new FormData(form);
    const allowances = Object.fromEntries(Object.keys(COSTS).flatMap(key => {
      const raw = fields.get("allow_" + key); return raw ? [[key, Number(raw)]] : [];
    }));
    const payload = {
      region:fields.get("region"), departure:fields.get("departure"), days:Number(fields.get("days")),
      people:Number(fields.get("people")), budget:Number(budgetValue.replace(/[., ]/g, "")),
      mode:fields.get("mode"), origin:fields.get("origin"), lodging_type:fields.get("lodging_type"),
      interests:fields.getAll("interests"), allowances,
    };
    displayError("");
    primary.disabled = true;
    primary.textContent = "Đang tạo lịch trình…";
    form.setAttribute("aria-busy", "true");
    setTriggerValue("submitted", payload);
  };
  if (data.sequence && Number(form.dataset.seen || 0) !== data.sequence) {
    form.dataset.seen = String(data.sequence);
    primary.disabled = false; primary.textContent = "Tạo lịch trình"; form.removeAttribute("aria-busy");
    if (data.error) {
      results.hidden = true; displayError(data.error);
    } else if (data.plan) {
      displayError("");
      renderPlan(results, data.plan);
      requestAnimationFrame(() => {
        results.scrollIntoView({block:"start"});
        results.querySelector("h2")?.focus({preventScroll:true});
      });
    }
  }
}
