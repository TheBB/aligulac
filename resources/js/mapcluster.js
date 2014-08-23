$(document).ready(function () {
    var autocomp_strings = {race: 'Race', name: 'Name'}
    var players = [];
    var geojson,
		    metadata,
		    iconField = '5065',
		    popupFields = ['5065', '5066'],
		    tileServer = 'http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
		    tileAttribution = 'Map data: <a href="http://openstreetmap.org">OSM</a>',
		    rmax = 30,
		    markerclusters = L.markerClusterGroup({
		        maxClusterRadius: 2 * rmax,
		        iconCreateFunction: defineClusterIcon
		    }),
        map = new L.Map('map');

    var convertPlayerJsonToMarkerObject = function (json) {
        var deferred = $.Deferred();
        var result = {};
        if (json) {
            $.when(getCoordinatesByCountryCode(json.country)).then(function (res) {
                result.geometry = { coordinates: [+res.lon, +res.lat], type: 'Point' };
                result.properties = { 5065: json.race, 5066: json.name };
                result.type = 'Feature';
                deferred.resolve({ res: result });
            });
        } else {
            deferred.resolve({ res: {} });
        }
        return deferred;
    };

    var makeMapCluster = function (playersJson) {
        var ajaxArray = [];
        var deferred = $.Deferred();
        for (var k = 0; k < playersJson.length; k++) {
            ajaxArray.push(convertPlayerJsonToMarkerObject(playersJson[k]));
        }
        $.when.apply(null, ajaxArray).then(function () {
            var featuresArray = [];
            for (var j = 0; j < arguments.length; j++) {
                featuresArray.push(arguments[j].res);
            }
            deferred.resolve({
                res: {
                    type: "FeatureCollection",
                    features: featuresArray,
                    properties: {
                        attribution: "Starcraft 2 statistics at: <a href='http://aligulac.com' target='blank'>aligulac.com</a>",
                        description: "Starcraft 2 statistics",
                        fields: {
                            5065: {
                                lookup: [
                                    { short: 'T', full: 'Terran' },
                                    { short: 'Z', full: 'Zerg' },
                                    { short: 'P', full: 'Protoss' },
                                    { short: 'R', full: 'Random' }
                                ], name: autocomp_strings['race']
                            },
                            5066: {
                                name: autocomp_strings['name']
                            }
                        }
                    }
                }
            });
        });
        return deferred;
    };

    var getCoordinatesByCountryCode = function (countryCode) {
        var deferred = $.Deferred();
        $.ajax({
            url: 'http://nominatim.openstreetmap.org/search?',
            data: { q: countryCode, format: 'json' }
        }).success(function (data) {
            if (data) {
                deferred.resolve({
                    "lat": data[0].lat, "lon": data[0].lon
                });
            } else {
                deferred.resolve({
                    "lat": 0, "lon": 0
                });
            }
        });
        return deferred;
    };

    var pushJsonToLink = function (linkCssClass, race, country, tag) {
        $(document).ready(function () {
            var json = eval($(linkCssClass).attr('data-players'));
            json.push({ 'race': race, 'country': country, 'name': tag });
        });
    }

    $('.show-players-map-link').click(function () {
        players = eval($(this).attr('data-players'));
        $('#playersMap').modal({
            show: true
        });
        return false;
    });
    $('#playersMap').on('hide.bs.modal', function () {
        markerclusters.clearLayers();
    });

    $('#playersMap').on('show.bs.modal', function (e) {
        L.tileLayer(tileServer, { attribution: tileAttribution, maxZoom: 15 }).addTo(map);
        map.addLayer(markerclusters);

        $.when(makeMapCluster(players)).then(function (data) {
            geojson = data.res;
            metadata = data.res.properties;
            var markers = L.geoJson(geojson, {
                pointToLayer: defineFeature,
                onEachFeature: defineFeaturePopup
            });
            markerclusters.addLayer(markers);
            map.fitBounds(markers.getBounds());
            map.attributionControl.addAttribution(metadata.attribution);
            renderLegend();
        });
    })

    function defineFeature(feature, latlng) {
        var iconVal = feature.properties[iconField];
        var myClass = 'marker race-ico icon-' + iconVal;
        var myIcon = L.divIcon({
            className: myClass,
            iconSize: null
        });
        return L.marker(latlng, { icon: myIcon });
    }

    function defineFeaturePopup(feature, layer) {
        var props = feature.properties,
			fields = metadata.fields,
			popupContent = '';

        popupFields.map(function (key) {
            if (props[key]) {
                var val = props[key],
					label = fields[key].name;
                if (fields[key].lookup) {
                    for (var j = 0; j < fields[key].lookup.length; j++) {
                        if (val === fields[key].lookup[j].short) {
                            val = fields[key].lookup[j].full;
                            break;
                        }
                    }
                }
                popupContent += '<span class="attribute"><span class="label">' + label + ':</span> ' + val + '</span><br/>';
            }
        });
        popupContent = '<div class="map-popup">' + popupContent + '</div>';
        layer.bindPopup(popupContent, { offset: L.point(1, -2) });
    }

    function defineClusterIcon(cluster) {
        var children = cluster.getAllChildMarkers(),
			n = children.length,
			strokeWidth = 1,
			r = rmax - 2 * strokeWidth - (n < 10 ? 12 : n < 100 ? 8 : n < 1000 ? 4 : 0),
			iconDim = (r + strokeWidth) * 2,
			data = d3.nest()
				.key(function (d) { return d.feature.properties[iconField]; })
				.entries(children, d3.map),
			html = bakeThePie({
			    data: data,
			    valueFunc: function (d) { return d.values.length; },
			    strokeWidth: 1,
			    outerRadius: r,
			    innerRadius: r - 10,
			    pieClass: 'cluster-pie',
			    pieLabel: n,
			    pieLabelClass: 'marker-cluster-pie-label',
			    pathClassFunc: function (d) { return "category-" + d.data.key; },
			    pathTitleFunc: function (d) { return metadata.fields[iconField].lookup[d.data.key] + ' (' + d.data.values.length + ' player' + (d.data.values.length != 1 ? 's' : '') + ')'; }
			}),
			myIcon = new L.DivIcon({
			    html: html,
			    className: 'marker-cluster',
			    iconSize: new L.Point(iconDim, iconDim)
			});
        return myIcon;
    }

    function bakeThePie(options) {
        if (!options.data || !options.valueFunc) {
            return '';
        }
        var data = options.data,
			valueFunc = options.valueFunc,
			r = options.outerRadius ? options.outerRadius : 28,
			rInner = options.innerRadius ? options.innerRadius : r - 10,
			strokeWidth = options.strokeWidth ? options.strokeWidth : 1,
			pathClassFunc = options.pathClassFunc ? options.pathClassFunc : function () { return ''; },
			pathTitleFunc = options.pathTitleFunc ? options.pathTitleFunc : function () { return ''; },
			pieClass = options.pieClass ? options.pieClass : 'marker-cluster-pie',
			pieLabel = options.pieLabel ? options.pieLabel : d3.sum(data, valueFunc),
			pieLabelClass = options.pieLabelClass ? options.pieLabelClass : 'marker-cluster-pie-label',
			origo = (r + strokeWidth),
			w = origo * 2,
			h = w,
			donut = d3.layout.pie(),
			arc = d3.svg.arc().innerRadius(rInner).outerRadius(r);

        var svg = document.createElementNS(d3.ns.prefix.svg, 'svg');
        var vis = d3.select(svg)
			.data([data])
			.attr('class', pieClass)
			.attr('width', w)
			.attr('height', h);

        var arcs = vis.selectAll('g.arc')
			.data(donut.value(valueFunc))
			.enter().append('svg:g')
			.attr('class', 'arc')
			.attr('transform', 'translate(' + origo + ',' + origo + ')');

        arcs.append('svg:path')
			.attr('class', pathClassFunc)
			.attr('stroke-width', strokeWidth)
			.attr('d', arc)
			.append('svg:title')
			.text(pathTitleFunc);

        vis.append('text')
			.attr('x', origo)
			.attr('y', origo)
			.attr('class', pieLabelClass)
			.attr('text-anchor', 'middle')
			.attr('dy', '.3em')
			.text(pieLabel);
        return serializeXmlNode(svg);
    }

    function renderLegend() {
        var data = d3.entries(metadata.fields[iconField].lookup),
			legenddiv = d3.select('#map').append('div')
				.attr('id', 'legend');

        var heading = legenddiv.append('div')
			.classed('legendheading', true)
			.text(metadata.fields[iconField].name);

        var legenditems = legenddiv.selectAll('.legenditem')
			.data(data);

        legenditems
			.enter()
			.append('div')
			.attr('class', function (d) { return 'category-' + d.value.short; })
			.classed({ 'legenditem': true })
			.text(function (d) { return d.value.full; });
    }

    function serializeXmlNode(xmlNode) {
        if (typeof window.XMLSerializer != "undefined") {
            return (new window.XMLSerializer()).serializeToString(xmlNode);
        } else if (typeof xmlNode.xml != "undefined") {
            return xmlNode.xml;
        }
        return "";
    }
});