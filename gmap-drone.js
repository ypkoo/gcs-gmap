var map;
var startLatLng_ADD = {lat: 36.426060, lng: 127.309237}
var startLatLng = {lat: 36.374092, lng: 127.365638}
var startLatLng2 = {lat: 36.374383, lng: 127.365327}
var marker;
var droneList = [];
var lineList = [];
var gcsMarker;

var lineSymbol = {
	path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW
};

function struct_drone() {
	var marker = '';
	var id = '';
	var infoWindow = '';
}

function initMap() {
	map = new google.maps.Map(document.getElementById('map'), {
		center: startLatLng,
		zoom: 19,
		mapTypeId: google.maps.MapTypeId.HYBRID
	});

	// var image = 'images/drone.png';
	map.addListener('click', map_clicked);

	// test marker
	gcsMarker = new google.maps.Marker({
		position: startLatLng,
		icon: 'http://maps.google.com/mapfiles/ms/icons/green-dot.png',
		// label: 'G'
	});



	var test_marker = new google.maps.Marker({
		position: startLatLng,
		// icon: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png',
		map: map,
		label: '1'
	});


	test_marker.addListener('click', function() {

		markerPos = test_marker.getPosition()
		gcsPos = gcsMarker.getPosition()

		if (gcsMarker.getMap() != null) {
			dist = google.maps.geometry.spherical.computeDistanceBetween (markerPos, gcsPos);
		}
		else {
			dist = "no_gcs_position";
		}

		jsCommunicator.emit_signal("marker_click_event " + '1' + " " + dist);
	});

}

function map_clicked(e) {
	var latLng = e.latLng;
	var lat = latLng.lat();
	var lng = latLng.lng();

	jsCommunicator.emit_signal("map_click_event " + lat + " " + lng);
}


function update_marker(id, lat, lng) {

	var idx = droneList.length;
	// existing drone
	for(var i=0; i<idx; i++) {
		if (id == droneList[i].id) {
			droneList[i].marker.setPosition({lat: lat, lng: lng});
			droneList[i].marker.setMap(map);
			// droneList[i].infoWindow.setContent(infoString);
			return;
		}
	}
	// new drone
	var marker = new google.maps.Marker({
		position: {lat: lat, lng: lng},
		// icon: 'http://maps.google.com/mapfiles/ms/icons/red-dot.png',
		map: map,
		label: id
	});


	marker.addListener('click', function() {
		markerPos = marker.getPosition()
		gcsPos = gcsMarker.getPosition()

		if (gcsMarker.getMap() != null) {
			dist = google.maps.geometry.spherical.computeDistanceBetween ({lat: lat1, lng: lng1}, {lat: lat2, lng: lng2});
		}
		else {
			dist = "no_gcs_position";
		}
		

		jsCommunicator.emit_signal("marker_click_event " + id + " " + dist);
	});

	droneList[idx] = new struct_drone();
	droneList[idx].marker = marker;
	droneList[idx].id = id;
	// droneList[idx].infoWindow = infoWindow;
}


function remove_marker(id) {

	var idx = droneList.length;
	for(var i=0; i<idx; i++) {
		if (id == droneList[i].id) {
			droneList[i].marker.setMap(null);
			droneList[i] = null;
			break;
		}
	}
}

function remove_all_markers() {
	var idx = droneList.length;
	for (var i=0; i<idx; i++) {
		droneList[i].marker.setMap(null);
	}

	markerList = [];
}

function draw_line(startLat, startLng, endLat, endLng) {
	var line = new google.maps.Polyline({
		path: [{lat: startLat, lng: startLng}, {lat: endLat, lng: endLng}],
		icons: [{
			icon: lineSymbol,
			offset: '100%'
		}],
		// geodesic: true,
		// strokeColor: '#FF0000',
		// strokeOpacity: 1.0,
		// strokeWeight: 2,
		map: map
	});
	// console.log(startLat);

	// var lineCoordinate = [{lat: startLat, lng: startLng}, {lat: endLat, lng: endLng}];
 //  var line = new google.maps.Polyline({
 //    path: lineCoordinate,
 //    geodesic: true,
 //    strokeColor: '#FF0000',
 //    strokeOpacity: 1.0,
 //    strokeWeight: 2
 //  });

 //  line.setMap(map);



	lineList.push(line);
}

function remove_all_lines() {
	for (var i=0; i<lineList.length; i++) {
		lineList[i].setMap(null);
	}

	lineList = [];
}


function mark_gcs_position(lat, lng) {
	gcsMarker.setPosition({lat: lat, lng: lng});
	gcsMarker.setMap(map);
}

function distance(lat1, lng1, lat2, lng2) {
	return google.maps.geometry.spherical.computeDistanceBetween ({lat: lat1, lng: lng1}, {lat: lat2, lng: lng2});
}